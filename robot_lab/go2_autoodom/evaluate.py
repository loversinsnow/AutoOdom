"""Evaluate Stage 1 and Stage 2 on the same whole-trajectory test files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from .autoregression import rollout_closed_loop, rollout_stage1_legacy
from .checkpoints import load_checkpoint
from .data import expand_patterns, load_trajectory
from .metrics import trajectory_metrics


def _evaluate_checkpoint(
    checkpoint_path: Path,
    trajectories,
    device: torch.device,
) -> dict[str, object]:
    model, checkpoint = load_checkpoint(checkpoint_path, map_location=device)
    model.to(device)
    stage = int(checkpoint["stage"])
    per_file = {}
    for trajectory in trajectories:
        if stage == 1:
            rollout = rollout_stage1_legacy(
                model,
                trajectory,
                checkpoint["feature_mean"],
                checkpoint["feature_std"],
                device=device,
            )
        else:
            rollout = rollout_closed_loop(
                model,
                trajectory,
                checkpoint["feature_mean"],
                checkpoint["feature_std"],
                stage=2,
                device=device,
            )
        per_file[trajectory.path.name] = trajectory_metrics(
            rollout.predictions,
            trajectory.pos_increment_hist,
            trajectory.base_rot_mat,
            trajectory.root_pos_abs,
        )
    metric_names = next(iter(per_file.values())).keys()
    aggregate = {
        metric: float(np.mean([metrics[metric] for metrics in per_file.values()])) for metric in metric_names
    }
    return {"stage": stage, "aggregate": aggregate, "per_file": per_file}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", nargs="+", required=True)
    parser.add_argument("--stage1-checkpoint", type=Path)
    parser.add_argument("--stage2-checkpoint", type=Path)
    parser.add_argument("--split-json", type=Path, help="Optional split.json produced by Stage 1 or Stage 2")
    parser.add_argument("--split", choices=("train", "validation", "test"), default="test")
    parser.add_argument("--output", type=Path, default=Path("outputs/go2_autoodom/evaluation.json"))
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()
    if args.stage1_checkpoint is None and args.stage2_checkpoint is None:
        parser.error("Pass at least one checkpoint")
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    files = expand_patterns(args.data)
    if args.split_json is not None:
        split_path = args.split_json.expanduser().resolve()
        split = json.loads(split_path.read_text(encoding="utf-8"))
        selected_names = set(split[args.split])
        selected_files = [path for path in files if path.name in selected_names]
        missing = selected_names - {path.name for path in selected_files}
        if missing:
            raise FileNotFoundError(
                f"{split_path} references files not matched by --data: {sorted(missing)}"
            )
        files = selected_files
        if not files:
            raise ValueError(f"{split_path} contains no files for split {args.split!r}")
    trajectories = [
        load_trajectory(path, require_acceleration=args.stage2_checkpoint is not None)
        for path in files
    ]
    results = {}
    if args.stage1_checkpoint:
        results["stage1"] = _evaluate_checkpoint(args.stage1_checkpoint, trajectories, device)
    if args.stage2_checkpoint:
        results["stage2"] = _evaluate_checkpoint(args.stage2_checkpoint, trajectories, device)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps({key: value["aggregate"] for key, value in results.items()}, indent=2))
    print(f"Saved detailed metrics to {args.output.resolve()}")


if __name__ == "__main__":
    main()
