"""Evaluate Stage 1 Go2 AutoOdom closed-loop navigation in MuJoCo."""

from __future__ import annotations

import argparse
from pathlib import Path

from .artifacts import (
    SIMULATION_EVAL_LOG_ROOT,
    SIMULATION_LOG_ROOT,
    create_timestamped_run,
    ensure_run_dir,
    resolve_evaluation_bundle,
)
from .checkpoints import sha256_file
from .eval_commands import (
    EVAL_COMMAND_PATH,
    load_eval_commands,
    load_origin2_relative_pose,
    sha256_file as command_sha256,
)
from .eval_core import CommandEvaluator, EvaluationConfig
from .inference import OnlineAutoOdom
from .mujoco_backend import DEFAULT_MUJOCO_XML, MujocoGo2Backend
from .real.policy import Go2LocomotionPolicy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--load_run",
        "--load-run",
        dest="load_run",
        help="Simulation timestamp or run directory; defaults to the latest complete run",
    )
    parser.add_argument("--log-root", type=Path, default=SIMULATION_LOG_ROOT)
    parser.add_argument("--deployment", type=Path, help="Explicit deployment.json override")
    parser.add_argument("--odometry-checkpoint", type=Path, help="Explicit Stage 1 checkpoint override")
    parser.add_argument("--eval-log-root", type=Path, default=SIMULATION_EVAL_LOG_ROOT)
    parser.add_argument("--output-dir", type=Path, help="Explicit evaluation output directory")
    parser.add_argument("--command-file", type=Path, default=EVAL_COMMAND_PATH)
    parser.add_argument("--command-start", type=int, default=1)
    parser.add_argument("--command-count", type=int, default=100)
    parser.add_argument("--average-speed", type=float, default=0.8)
    parser.add_argument("--final-speed", type=float, default=0.8)
    parser.add_argument("--time-scale", type=float, default=1.01)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--mujoco-xml", type=Path, default=DEFAULT_MUJOCO_XML)
    parser.add_argument("--settle-time", type=float, default=2.0)
    parser.add_argument("--viewer", action="store_true")
    parser.add_argument("--realtime", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    bundle = resolve_evaluation_bundle(
        args.log_root,
        stage=1,
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
    print(f"[Eval] simulation run: {bundle.run_dir}")
    print(f"[Eval] locomotion policy: {bundle.policy_path}")
    print(f"[Eval] Stage 1 odometry: {bundle.odometry_checkpoint}")
    print(f"[Eval] output: {output_dir}")

    policy = Go2LocomotionPolicy(bundle.deployment_json, device=args.device)
    estimator = OnlineAutoOdom(bundle.odometry_checkpoint, device=args.device)
    if estimator.stage != 1:
        raise ValueError(f"MuJoCo evaluation requires Stage 1 odometry, got Stage {estimator.stage}")
    backend = MujocoGo2Backend(
        args.mujoco_xml,
        viewer=args.viewer,
        realtime=args.realtime,
    )
    try:
        backend.settle(args.settle_time)
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
                "backend": "mujoco",
                "training_stage": 1,
                "training_domain": "simulation",
                "source_run": bundle.run_dir,
                "deployment_json": bundle.deployment_json,
                "policy_sha256": sha256_file(bundle.policy_path),
                "odometry_checkpoint": bundle.odometry_checkpoint,
                "odometry_sha256": sha256_file(bundle.odometry_checkpoint),
                "command_file": Path(args.command_file).expanduser().resolve(),
                "command_sha256": command_sha256(args.command_file),
                "mujoco_xml": Path(args.mujoco_xml).expanduser().resolve(),
                "mujoco_xml_sha256": sha256_file(args.mujoco_xml),
            },
        )
    finally:
        backend.close()
    summary = payload["summary"]
    print(
        f"[SUCCESS] MuJoCo evaluation: {summary['successful_commands']}/"
        f"{summary['completed_commands']} commands, report={output_dir / 'summary.json'}"
    )
    if summary["aborted"]:
        raise RuntimeError(str(summary["aborted_reason"]))


if __name__ == "__main__":
    main()
