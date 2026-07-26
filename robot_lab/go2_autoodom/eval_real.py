"""Evaluate Stage 2 Go2 AutoOdom navigation using mocap as ground truth."""

from __future__ import annotations

import argparse
from pathlib import Path

from .artifacts import (
    REAL_EVAL_LOG_ROOT,
    REAL_LOG_ROOT,
    create_timestamped_run,
    ensure_run_dir,
    resolve_evaluation_bundle,
)
from .checkpoints import sha256_file
from .constants import DEFAULT_UNITREE_SDK_DIR
from .eval_commands import (
    EVAL_COMMAND_PATH,
    load_eval_commands,
    load_origin2_relative_pose,
    sha256_file as command_sha256,
)
from .eval_core import CommandEvaluator, EvaluationConfig
from .inference import OnlineAutoOdom
from .real import Go2LowLevelInterface, MocapTracker, stop_sport_mode
from .real.evaluation import RealGo2EvaluationBackend
from .real.policy import Go2LocomotionPolicy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--load_run",
        "--load-run",
        dest="load_run",
        help="Real timestamp or run directory; defaults to the latest complete run",
    )
    parser.add_argument("--log-root", type=Path, default=REAL_LOG_ROOT)
    parser.add_argument("--deployment", type=Path, help="Explicit deployment.json override")
    parser.add_argument("--odometry-checkpoint", type=Path, help="Explicit Stage 2 checkpoint override")
    parser.add_argument("--eval-log-root", type=Path, default=REAL_EVAL_LOG_ROOT)
    parser.add_argument("--output-dir", type=Path, help="Explicit evaluation output directory")
    parser.add_argument("--command-file", type=Path, default=EVAL_COMMAND_PATH)
    parser.add_argument("--command-start", type=int, default=1)
    parser.add_argument("--command-count", type=int, default=100)
    parser.add_argument("--average-speed", type=float, default=0.8)
    parser.add_argument("--final-speed", type=float, default=0.8)
    parser.add_argument("--time-scale", type=float, default=1.01)
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Publish to rt/lowcmd; default uses an isolated dry-run topic",
    )
    parser.add_argument("--network-interface", help="Required with --live; dry-run defaults to eno1")
    parser.add_argument("--unitree-sdk-path", type=Path, default=DEFAULT_UNITREE_SDK_DIR)
    parser.add_argument("--ros-setup", action="append", default=["/opt/ros/rolling/setup.zsh"])
    parser.add_argument("--mocap-timeout", type=float, default=0.5)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.live and not args.network_interface:
        parser.error("--live requires --network-interface <iface>")

    bundle = resolve_evaluation_bundle(
        args.log_root,
        stage=2,
        load_run=args.load_run,
        deployment_override=args.deployment,
        odometry_override=args.odometry_checkpoint,
    )
    commands = load_eval_commands(
        args.command_file,
        start=args.command_start,
        count=args.command_count,
    )
    output_dir = (
        ensure_run_dir(args.output_dir)
        if args.output_dir is not None
        else create_timestamped_run(args.eval_log_root)
    )
    config = EvaluationConfig(
        average_speed=args.average_speed,
        final_speed=args.final_speed,
        time_scale=args.time_scale,
    )
    print(f"[Eval] real run: {bundle.run_dir}")
    print(f"[Eval] locomotion policy: {bundle.policy_path}")
    print(f"[Eval] Stage 2 odometry: {bundle.odometry_checkpoint}")
    print(f"[Eval] output: {output_dir}")
    if not args.live:
        print(
            "[DRY-RUN] Commands publish only to an isolated DDS topic. "
            "The robot will not move, so command outcomes are expected to time out."
        )

    policy = Go2LocomotionPolicy(bundle.deployment_json, device=args.device)
    estimator = OnlineAutoOdom(bundle.odometry_checkpoint, device=args.device)
    if estimator.stage != 2:
        raise ValueError(f"Real evaluation requires Stage 2 odometry, got Stage {estimator.stage}")

    network_interface = args.network_interface or "eno1"
    controller = Go2LowLevelInterface(
        network_interface=network_interface,
        live=args.live,
        sdk_path=args.unitree_sdk_path,
    )
    mocap = None
    try:
        mocap = MocapTracker(
            ros_setups=tuple(args.ros_setup),
            timeout=args.mocap_timeout,
        )
        backend = RealGo2EvaluationBackend(controller, mocap)
        controller.wait_for_state()
        mocap.wait_ready()
        if args.live:
            stop_sport_mode(
                network_interface,
                sdk_path=args.unitree_sdk_path,
                initialize_channel=False,
            )
        controller.prepare_for_policy()
        backend.reset_timing()
        evaluator = CommandEvaluator(
            backend=backend,
            policy=policy,
            estimator=estimator,
            output_dir=output_dir,
            origin2_relative_pose=load_origin2_relative_pose(),
            config=config,
        )
        payload = evaluator.run(
            commands,
            metadata={
                "backend": "real_go2_mocap",
                "live_control": args.live,
                "training_stage": 2,
                "training_domain": "real",
                "source_run": bundle.run_dir,
                "deployment_json": bundle.deployment_json,
                "policy_sha256": sha256_file(bundle.policy_path),
                "odometry_checkpoint": bundle.odometry_checkpoint,
                "odometry_sha256": sha256_file(bundle.odometry_checkpoint),
                "command_file": Path(args.command_file).expanduser().resolve(),
                "command_sha256": command_sha256(args.command_file),
            },
        )
    finally:
        controller.shutdown()
        if mocap is not None:
            mocap.close()
    summary = payload["summary"]
    print(
        f"[SUCCESS] Real mocap evaluation: {summary['successful_commands']}/"
        f"{summary['completed_commands']} commands, report={output_dir / 'summary.json'}"
    )
    if summary["aborted"]:
        raise RuntimeError(str(summary["aborted_reason"]))


if __name__ == "__main__":
    main()
