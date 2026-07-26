"""Collect continuous 50 Hz Go2 simulation trajectories for AutoOdom Stage 1."""

from __future__ import annotations

import argparse
from pathlib import Path

from isaaclab.app import AppLauncher

from .artifacts import data_dir, ensure_run_dir, latest_model_checkpoint, update_run_manifest
from .constants import GO2_JOINT_NAMES, HISTORY_LENGTH, PLAY_TASK_ID, SAMPLE_DT


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--checkpoint", type=Path)
parser.add_argument(
    "--run-dir",
    type=Path,
    help="Stage 1 timestamp directory; inferred from --checkpoint when omitted",
)
parser.add_argument("--task", default=PLAY_TASK_ID)
parser.add_argument("--output-dir", type=Path, help="Legacy direct data-directory override")
parser.add_argument(
    "--steps",
    type=int,
    default=10_000,
    help="Number of valid 50 Hz samples saved in each trajectory",
)
parser.add_argument(
    "--num-trajectories",
    type=int,
    default=1,
    help="Number of independent trajectory files to collect in this simulator session",
)
parser.add_argument(
    "--max-restarts",
    type=int,
    default=20,
    help="Maximum fall/discontinuity restarts allowed while collecting each trajectory",
)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
if args.checkpoint is None and args.run_dir is None:
    parser.error("Pass --run-dir or --checkpoint")
if args.steps <= HISTORY_LENGTH:
    parser.error(f"--steps must be greater than the {HISTORY_LENGTH}-frame Stage 1 history")
if args.num_trajectories < 1:
    parser.error("--num-trajectories must be at least 1")
if args.max_restarts < 0:
    parser.error("--max-restarts cannot be negative")

app_launcher = AppLauncher(args)
simulation_app = app_launcher.app

import gymnasium as gym
import numpy as np
import torch
from rsl_rl.runners import OnPolicyRunner

from isaaclab.utils.math import matrix_from_quat
from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper
from isaaclab_tasks.utils import parse_env_cfg
from isaaclab_tasks.utils.parse_cfg import load_cfg_from_registry

from . import isaaclab_task  # noqa: F401, E402
from .data import save_trajectory


def _next_path(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    index = 0
    while (directory / f"go2_stage1_sim_{index:04d}.npz").exists():
        index += 1
    return directory / f"go2_stage1_sim_{index:04d}.npz"


def main() -> None:
    run_dir = ensure_run_dir(args.run_dir) if args.run_dir else None
    checkpoint = (
        args.checkpoint.expanduser().resolve() if args.checkpoint is not None else latest_model_checkpoint(run_dir)
    )
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    if run_dir is None:
        run_dir = checkpoint.parent
    elif checkpoint.parent != run_dir:
        raise ValueError(f"{checkpoint} is not stored directly in Stage 1 run directory {run_dir}")
    deployment_dir = run_dir / "exported"
    for required_artifact in ("policy.pt", "deployment.json"):
        path = deployment_dir / required_artifact
        if not path.is_file():
            raise FileNotFoundError(
                f"{path} is missing; export the control policy into the same timestamp directory first"
            )
    output_dir = args.output_dir.expanduser().resolve() if args.output_dir else data_dir(run_dir, "sim")
    update_run_manifest(
        run_dir,
        stage=1,
        training_domain="simulation",
        extra={"policy_checkpoint": checkpoint.name},
    )
    env_cfg = parse_env_cfg(args.task, device=args.device, num_envs=1)
    env_cfg.observations.policy.enable_corruption = False
    # The upstream play task times out after 20 seconds. A Stage 1 trajectory must
    # remain continuous, so keep this collection episode alive for the requested
    # number of 50 Hz samples instead of silently stitching timeout resets together.
    env_cfg.episode_length_s = max(
        float(env_cfg.episode_length_s),
        (args.steps + 2) * SAMPLE_DT,
    )
    agent_cfg = load_cfg_from_registry(args.task, "rsl_rl_cfg_entry_point")
    agent_cfg.device = args.device
    raw_env = gym.make(args.task, cfg=env_cfg)
    env = RslRlVecEnvWrapper(raw_env, clip_actions=agent_cfg.clip_actions)
    runner = OnPolicyRunner(env, agent_cfg.to_dict(), log_dir=None, device=agent_cfg.device)
    runner.load(str(checkpoint))
    policy = runner.get_inference_policy(device=raw_env.unwrapped.device)

    robot = raw_env.unwrapped.scene["robot"]
    joint_ids, resolved_names = robot.find_joints(list(GO2_JOINT_NAMES), preserve_order=True)
    if tuple(resolved_names) != GO2_JOINT_NAMES:
        raise RuntimeError(f"Isaac Lab resolved a different joint order: {resolved_names}")
    base_ids, _ = robot.find_bodies("base", preserve_order=True)
    base_id = base_ids[0]
    log_names = (
        "joint_pos",
        "joint_vel",
        "joint_commands",
        "gyro_ang_vel",
        "imu_lin_acc",
        "base_rot_mat",
        "cmd_vel",
        "pos_increment_hist",
        "root_pos_abs",
    )
    outputs: list[Path] = []

    with torch.inference_mode():
        for trajectory_index in range(args.num_trajectories):
            observation, _ = env.reset()
            previous_root = robot.data.root_pos_w.clone()
            log = {name: [] for name in log_names}
            restart_count = 0
            print(f"[INFO] Collecting trajectory {trajectory_index + 1}/{args.num_trajectories}: {args.steps} samples")

            while len(log["joint_pos"]) < args.steps:
                actions = torch.clamp(policy(observation), -1.0, 1.0)
                observation, _, dones, _ = env.step(actions)
                current_root = robot.data.root_pos_w
                rotations = matrix_from_quat(robot.data.root_quat_w)
                jump = torch.linalg.vector_norm(current_root - previous_root, dim=1) > 0.5
                if bool(torch.any(dones | jump)):
                    restart_count += 1
                    if restart_count > args.max_restarts:
                        raise RuntimeError(
                            f"Trajectory {trajectory_index + 1} exceeded --max-restarts={args.max_restarts}; "
                            "check the locomotion policy before collecting Stage 1 data"
                        )
                    discarded = len(log["joint_pos"])
                    for values in log.values():
                        values.clear()
                    if not bool(torch.any(dones)):
                        observation, _ = env.reset()
                    previous_root = robot.data.root_pos_w.clone()
                    print(
                        f"[WARN] Restarting trajectory {trajectory_index + 1}/{args.num_trajectories} "
                        f"after a reset/discontinuity; discarded {discarded} samples "
                        f"({restart_count}/{args.max_restarts})"
                    )
                    continue

                delta_world = (current_root - previous_root).unsqueeze(-1)
                delta_local = torch.bmm(rotations.transpose(1, 2), delta_world).squeeze(-1)
                acceleration_world = robot.data.body_lin_acc_w[:, base_id, :]
                acceleration_body = torch.bmm(
                    rotations.transpose(1, 2),
                    acceleration_world.unsqueeze(-1),
                ).squeeze(-1)
                command = raw_env.unwrapped.command_manager.get_command("base_velocity")
                log["joint_pos"].append(robot.data.joint_pos[:, joint_ids].cpu().numpy()[0])
                log["joint_vel"].append(robot.data.joint_vel[:, joint_ids].cpu().numpy()[0])
                log["joint_commands"].append(actions.cpu().numpy()[0])
                log["gyro_ang_vel"].append(robot.data.root_ang_vel_b.cpu().numpy()[0])
                log["imu_lin_acc"].append(acceleration_body.cpu().numpy()[0])
                log["base_rot_mat"].append(rotations.cpu().numpy()[0])
                log["cmd_vel"].append(command.cpu().numpy()[0])
                log["pos_increment_hist"].append(delta_local.cpu().numpy()[0])
                log["root_pos_abs"].append(current_root.cpu().numpy()[0])
                previous_root = current_root.clone()
                if len(log["joint_pos"]) % 1000 == 0:
                    print(
                        f"trajectory {trajectory_index + 1}/{args.num_trajectories}: "
                        f"collected {len(log['joint_pos'])}/{args.steps}"
                    )

            arrays = {name: np.asarray(values, dtype=np.float32) for name, values in log.items()}
            output = save_trajectory(_next_path(output_dir), arrays, source="sim_go2")
            outputs.append(output)
            print(f"[SUCCESS] Saved trajectory {trajectory_index + 1}/{args.num_trajectories}: {output}")

    print(f"[SUCCESS] Collected {len(outputs)} Stage 1 trajectories in {output_dir.resolve()}")
    raw_env.close()


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
