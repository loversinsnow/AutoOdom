"""Fine-tune Stage 1 with real mocap labels, acceleration, and self-prediction feedback."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch

from .artifacts import (
    STAGE2_BEST_FILENAME,
    STAGE2_LAST_FILENAME,
    atomic_torch_save,
    ensure_run_dir,
    odometry_dir,
    update_run_manifest,
)
from .autoregression import rollout_closed_loop, train_stage2_trajectory
from .checkpoints import checkpoint_payload, load_checkpoint, sha256_file
from .data import (
    expand_patterns,
    load_trajectory,
    split_files,
    split_manifest_json,
    trajectory_manifest,
)
from .model import expand_stage1_to_stage2


def _device(name: str) -> torch.device:
    if name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", nargs="+", required=True, help="Real Go2 mocap .npz paths or glob patterns")
    parser.add_argument("--stage1-checkpoint", type=Path, required=True)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument(
        "--run-dir",
        type=Path,
        help="Stage 2 timestamp directory containing the real-run exported policy",
    )
    destination.add_argument(
        "--output-dir",
        type=Path,
        help="Legacy direct odometry-directory override",
    )
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--learning-rate", type=float, default=1.0e-4)
    parser.add_argument("--chunk-size", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    run_dir = ensure_run_dir(args.run_dir) if args.run_dir else None
    if run_dir is not None:
        for relative_path in ("exported/policy.pt", "exported/deployment.json"):
            if not (run_dir / relative_path).is_file():
                raise FileNotFoundError(
                    f"{run_dir / relative_path} is missing; Stage 2 policy and odometry must share one run"
                )
        output_dir = odometry_dir(run_dir)
    else:
        output_dir = args.output_dir.expanduser().resolve()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    files = expand_patterns(args.data)
    train_files, validation_files, test_files = split_files(files, seed=args.seed)
    train_trajectories = [
        load_trajectory(path, require_acceleration=True, expected_source_prefix="real") for path in train_files
    ]
    validation_trajectories = [
        load_trajectory(path, require_acceleration=True, expected_source_prefix="real")
        for path in validation_files
    ]

    stage1_model, stage1_checkpoint = load_checkpoint(args.stage1_checkpoint, expected_stage=1)
    stage2_model = expand_stage1_to_stage2(stage1_model)
    stage1_mean = torch.as_tensor(stage1_checkpoint["feature_mean"], dtype=torch.float32)
    stage1_std = torch.as_tensor(stage1_checkpoint["feature_std"], dtype=torch.float32)
    acceleration = np.concatenate([trajectory.imu_lin_acc for trajectory in train_trajectories], axis=0)
    acceleration_mean = torch.from_numpy(acceleration.mean(axis=0).astype(np.float32))
    acceleration_std = torch.from_numpy((acceleration.std(axis=0) + 1.0e-8).astype(np.float32))
    feature_mean = torch.cat([stage1_mean, acceleration_mean])
    feature_std = torch.cat([stage1_std, acceleration_std])
    target_mean = torch.as_tensor(stage1_checkpoint["target_mean"], dtype=torch.float32)
    target_std = torch.as_tensor(stage1_checkpoint["target_std"], dtype=torch.float32)

    device = _device(args.device)
    stage2_model.to(device)
    optimizer = torch.optim.Adam(stage2_model.parameters(), lr=args.learning_rate, weight_decay=1.0e-5)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1.0e-6)
    rng = np.random.default_rng(args.seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "split.json").write_text(
        split_manifest_json(train_files, validation_files, test_files),
        encoding="utf-8",
    )

    train_losses: list[float] = []
    validation_losses: list[float] = []
    best_validation = float("inf")
    parent_sha = sha256_file(args.stage1_checkpoint)
    if run_dir is not None:
        update_run_manifest(
            run_dir,
            stage=2,
            training_domain="real",
            extra={"parent_stage1_sha256": parent_sha},
        )
    manifest = trajectory_manifest(files)
    print(
        f"Stage 2: {len(train_trajectories)} train / {len(validation_trajectories)} validation "
        f"real trajectories on {device}"
    )
    for epoch in range(1, args.epochs + 1):
        epoch_mse = []
        for trajectory_index in rng.permutation(len(train_trajectories)):
            result = train_stage2_trajectory(
                stage2_model,
                train_trajectories[int(trajectory_index)],
                feature_mean,
                feature_std,
                optimizer,
                device=device,
                chunk_size=args.chunk_size,
            )
            epoch_mse.append(result.mse)
        train_loss = float(np.mean(epoch_mse))
        validation_loss = float(
            np.mean(
                [
                    rollout_closed_loop(
                        stage2_model,
                        trajectory,
                        feature_mean,
                        feature_std,
                        stage=2,
                        device=device,
                    ).mse
                    for trajectory in validation_trajectories
                ]
            )
        )
        scheduler.step()
        train_losses.append(train_loss)
        validation_losses.append(validation_loss)
        is_best = validation_loss < best_validation
        best_validation = min(best_validation, validation_loss)
        payload = checkpoint_payload(
            stage=2,
            epoch=epoch,
            model=stage2_model,
            optimizer=optimizer,
            feature_mean=feature_mean,
            feature_std=feature_std,
            target_mean=target_mean,
            target_std=target_std,
            best_validation_loss=best_validation,
            train_losses=train_losses,
            validation_losses=validation_losses,
            data_manifest=manifest,
            parent_stage1_sha256=parent_sha,
        )
        atomic_torch_save(payload, output_dir / STAGE2_LAST_FILENAME)
        if is_best:
            atomic_torch_save(payload, output_dir / STAGE2_BEST_FILENAME)
        print(
            f"epoch={epoch:04d} train_mse={train_loss:.6f} validation_mse={validation_loss:.6f} "
            f"lr={scheduler.get_last_lr()[0]:.2e}"
        )

    summary = {
        "best_validation_mse": best_validation,
        "parent_stage1_sha256": parent_sha,
        "train_files": len(train_files),
        "validation_files": len(validation_files),
        "test_files": len(test_files),
        "device": str(device),
        "training_domain": "real",
        "run_dir": str(run_dir) if run_dir is not None else None,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[SUCCESS] Stage 2 real odometry: {(output_dir / STAGE2_BEST_FILENAME).resolve()}")


if __name__ == "__main__":
    main()
