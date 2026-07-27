"""Run Go2 locomotion, collect mocap-labelled real data, and optionally infer AutoOdom online."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

from .artifacts import (
    REAL_LOG_ROOT,
    copy_deployment_bundle,
    create_timestamped_run,
    data_dir,
    ensure_run_dir,
    update_run_manifest,
)
from .constants import DEFAULT_UNITREE_SDK_DIR, SAMPLE_DT
from .data import save_trajectory
from .inference import OnlineAutoOdom
from .math_utils import local_increment
from .real import Go2LowLevelInterface, MocapTracker, stop_sport_mode
from .real.policy import Go2LocomotionPolicy


def _next_path(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    index = 0
    while (directory / f"go2_real_mocap_{index:04d}.npz").exists():
        index += 1
    return directory / f"go2_real_mocap_{index:04d}.npz"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployment", type=Path, required=True)
    destination = parser.add_mutually_exclusive_group()
    destination.add_argument("--run-dir", type=Path, help="Existing Stage 2 timestamp directory")
    destination.add_argument("--output-dir", type=Path, help="Legacy direct data-directory override")
    parser.add_argument("--log-root", type=Path, default=REAL_LOG_ROOT)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Publish to rt/lowcmd; default uses an isolated dry-run topic",
    )
    parser.add_argument("--network-interface", help="Required with --live; dry-run defaults to eno1")
    parser.add_argument("--unitree-sdk-path", type=Path, default=DEFAULT_UNITREE_SDK_DIR)
    parser.add_argument("--remote-command", action="store_true")
    parser.add_argument("--cmd-x", type=float, default=0.3)
    parser.add_argument("--cmd-y", type=float, default=0.0)
    parser.add_argument("--cmd-yaw", type=float, default=0.0)
    parser.add_argument("--stage1-checkpoint", type=Path)
    parser.add_argument("--stage2-checkpoint", type=Path)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--ros-setup", action="append", default=["/opt/ros/rolling/setup.zsh"])
    args = parser.parse_args()
    if args.live and not args.network_interface:
        parser.error("--live requires --network-interface <iface>")
    if args.stage1_checkpoint and args.stage2_checkpoint:
        parser.error("Pass at most one online AutoOdom checkpoint")

    if args.output_dir is not None:
        run_dir = None
        output_dir = args.output_dir.expanduser().resolve()
        deployment = args.deployment.expanduser().resolve()
    else:
        run_dir = ensure_run_dir(args.run_dir) if args.run_dir else create_timestamped_run(args.log_root)
        deployment = copy_deployment_bundle(args.deployment, run_dir)
        output_dir = data_dir(run_dir, "real")
        update_run_manifest(
            run_dir,
            stage=2,
            training_domain="real",
            extra={"control_policy_origin": "copied_for_real_data_collection"},
        )
        print(f"[INFO] Stage 2 real run: {run_dir}")

    network_interface = args.network_interface or "eno1"
    controller = Go2LowLevelInterface(
        network_interface=network_interface,
        live=args.live,
        sdk_path=args.unitree_sdk_path,
    )
    mocap = MocapTracker(ros_setups=tuple(args.ros_setup))
    policy = Go2LocomotionPolicy(deployment, device=args.device)
    estimator_path = args.stage2_checkpoint or args.stage1_checkpoint
    estimator = OnlineAutoOdom(estimator_path, device=args.device) if estimator_path else None
    fixed_command = np.clip(
        np.asarray([args.cmd_x, args.cmd_y, args.cmd_yaw], dtype=np.float32),
        -1.0,
        1.0,
    )
    log = {
        name: []
        for name in (
            "joint_pos",
            "joint_vel",
            "joint_commands",
            "gyro_ang_vel",
            "imu_lin_acc",
            "base_rot_mat",
            "mocap_rot_mat",
            "cmd_vel",
            "pos_increment_hist",
            "root_pos_abs",
            "mocap_twist_world",
        )
    }
    previous_pose = None
    previous_loop_time = None
    output_path = None

    try:
        controller.wait_for_state()
        mocap.wait_ready()
        if args.live:
            stop_sport_mode(
                network_interface,
                sdk_path=args.unitree_sdk_path,
                initialize_channel=False,
            )
        controller.prepare_for_policy()
        start = time.monotonic()
        next_tick = start
        while time.monotonic() - start < args.duration:
            loop_start = time.monotonic()
            if previous_loop_time is not None and loop_start - previous_loop_time > 0.10:
                print("[Go2] Control discontinuity detected; ending this trajectory.")
                break
            state = controller.read_state()
            command = state.remote.velocity_command() if args.remote_command else fixed_command
            policy_start = time.monotonic()
            action = policy.act(state, command)
            if time.monotonic() - policy_start > 0.10:
                raise TimeoutError("Locomotion policy inference timeout")
            controller.send_policy_action(action, state)
            pose = mocap.sample()
            if previous_pose is None:
                increment = np.zeros(3, dtype=np.float32)
            else:
                if np.linalg.norm(pose.position - previous_pose.position) > 0.5:
                    print("[Go2] Mocap discontinuity detected; ending this trajectory.")
                    break
                increment = local_increment(previous_pose.position, pose.position, pose.rotation)

            log["joint_pos"].append(state.joint_pos)
            log["joint_vel"].append(state.joint_vel)
            log["joint_commands"].append(action)
            log["gyro_ang_vel"].append(state.gyro)
            log["imu_lin_acc"].append(state.acceleration)
            log["base_rot_mat"].append(state.rotation)
            log["mocap_rot_mat"].append(pose.rotation)
            log["cmd_vel"].append(command)
            log["pos_increment_hist"].append(increment)
            log["root_pos_abs"].append(pose.position)
            twist = np.concatenate([
                pose.linear_velocity_world
                if pose.linear_velocity_world is not None
                else np.full(3, np.nan, dtype=np.float32),
                pose.angular_velocity_world
                if pose.angular_velocity_world is not None
                else np.full(3, np.nan, dtype=np.float32),
            ])
            log["mocap_twist_world"].append(twist)

            if estimator is not None:
                _, estimated_position = estimator.update(
                    joint_pos=state.joint_pos,
                    joint_vel=state.joint_vel,
                    gyro_ang_vel=state.gyro,
                    base_rot_mat=state.rotation,
                    joint_commands=action,
                    imu_lin_acc=state.acceleration,
                )
                if len(log["joint_pos"]) % 50 == 0:
                    mocap_relative = pose.position - log["root_pos_abs"][0]
                    print(
                        f"t={len(log['joint_pos']) * SAMPLE_DT:6.1f}s "
                        f"odom={estimated_position.round(3)} mocap={mocap_relative.round(3)}"
                    )
            previous_pose = pose
            previous_loop_time = loop_start
            next_tick += SAMPLE_DT
            remaining = next_tick - time.monotonic()
            if remaining > 0.0:
                time.sleep(remaining)
    except KeyboardInterrupt:
        print("[Go2] Interrupted; finalizing the continuous trajectory.")
    finally:
        controller.shutdown()
        mocap.close()
        if len(log["joint_pos"]) >= 2:
            arrays = {name: np.asarray(values, dtype=np.float32) for name, values in log.items()}
            # Twist may legitimately be unavailable; it is auxiliary and not part of model training.
            output_path = save_trajectory(_next_path(output_dir), arrays, source="real_go2_mocap")
            print(f"[SUCCESS] Saved {len(log['joint_pos'])} real frames to {output_path}")
        else:
            print("[WARN] Fewer than two synchronized frames; no trajectory was saved.")


if __name__ == "__main__":
    main()
