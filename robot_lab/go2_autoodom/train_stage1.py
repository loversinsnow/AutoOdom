"""Train the unchanged Stage 1 estimator on Go2 simulation trajectories."""

from __future__ import annotations

import argparse
import json
import random
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader

from .artifacts import (
    STAGE1_BEST_FILENAME,
    STAGE1_LAST_FILENAME,
    atomic_torch_save,
    ensure_run_dir,
    odometry_dir,
    update_run_manifest,
)
from .checkpoints import checkpoint_payload, load_checkpoint
from .data import (
    Stage1WindowDataset,
    compute_stage1_statistics,
    expand_patterns,
    load_trajectory,
    split_files,
    split_manifest_json,
    trajectory_manifest,
)
from .model import AutoOdomLoss, AutoOdomNet


def _device(name: str) -> torch.device:
    if name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(name)


def _resolve_resume_path(value: str | None, output_dir: Path) -> Path | None:
    if value is None:
        return None
    path = output_dir / STAGE1_LAST_FILENAME if value == "" else Path(value).expanduser()
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Stage 1 resume checkpoint is missing: {path}")
    return path


def _validate_resume_checkpoint(
    checkpoint: dict[str, Any],
    *,
    data_manifest: str,
    seed: int,
    total_epochs: int,
) -> int:
    completed_epoch = int(checkpoint.get("epoch", 0))
    if completed_epoch < 1:
        raise ValueError("Stage 1 resume checkpoint has no completed epoch")
    if completed_epoch >= total_epochs:
        raise ValueError(
            f"Stage 1 checkpoint already completed epoch {completed_epoch}; "
            f"--epochs must be a larger total, got {total_epochs}"
        )
    if checkpoint.get("optimizer_state_dict") is None:
        raise ValueError("Stage 1 resume checkpoint does not contain optimizer state")
    if checkpoint.get("data_manifest_sha256") != data_manifest:
        raise ValueError("Stage 1 resume data does not match the checkpoint data manifest")
    train_losses = list(checkpoint.get("train_losses", ()))
    validation_losses = list(checkpoint.get("validation_losses", ()))
    if len(train_losses) != completed_epoch or len(validation_losses) != completed_epoch:
        raise ValueError("Stage 1 resume checkpoint loss history does not match its completed epoch")
    training_config = checkpoint.get("training_config")
    if training_config is not None and int(training_config.get("seed", seed)) != seed:
        raise ValueError(f"Stage 1 resume checkpoint used seed={training_config.get('seed')}; got --seed={seed}")
    return completed_epoch


def _restore_scheduler(
    scheduler: torch.optim.lr_scheduler.CosineAnnealingLR,
    checkpoint: dict[str, Any],
    *,
    completed_epoch: int,
    total_epochs: int,
) -> str | None:
    scheduler_state = checkpoint.get("scheduler_state_dict")
    if scheduler_state is not None and int(scheduler_state.get("T_max", total_epochs)) == total_epochs:
        scheduler.load_state_dict(scheduler_state)
        if scheduler.last_epoch != completed_epoch:
            raise ValueError(
                f"Stage 1 scheduler is at epoch {scheduler.last_epoch}, "
                f"but the checkpoint model is at epoch {completed_epoch}"
            )
        return None

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        scheduler.step(completed_epoch)
    if scheduler_state is None:
        return "checkpoint predates scheduler-state saving; reconstructed the cosine schedule"
    return f"changed cosine schedule from {scheduler_state.get('T_max')} to {total_epochs} total epochs"


def _capture_rng_state(generator: torch.Generator, device: torch.device) -> dict[str, Any]:
    return {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch_cpu": torch.get_rng_state(),
        "torch_cuda": torch.cuda.get_rng_state(device) if device.type == "cuda" else None,
        "data_loader": generator.get_state(),
    }


def _restore_rng_state(
    state: dict[str, Any],
    *,
    generator: torch.Generator,
    device: torch.device,
) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch_cpu"])
    generator.set_state(state["data_loader"])
    if device.type == "cuda" and state.get("torch_cuda") is not None:
        torch.cuda.set_rng_state(state["torch_cuda"], device)


def _average_loss(
    model: AutoOdomNet,
    loader: DataLoader,
    criterion: AutoOdomLoss,
    mean: torch.Tensor,
    std: torch.Tensor,
    device: torch.device,
    optimizer: torch.optim.Optimizer | None,
) -> float:
    training = optimizer is not None
    model.train(training)
    total = 0.0
    context = torch.enable_grad() if training else torch.no_grad()
    with context:
        for features, target in loader:
            features = features.to(device)
            target = target.to(device)
            normalized = (features - mean) / std
            prediction = model(normalized)
            loss, _ = criterion(prediction, target)
            if optimizer is not None:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
            total += float(loss.detach()) * features.shape[0]
    return total / len(loader.dataset)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", nargs="+", required=True, help="Simulation .npz paths or glob patterns")
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument(
        "--run-dir",
        type=Path,
        help="Stage 1 timestamp directory containing exported/policy.pt",
    )
    destination.add_argument(
        "--output-dir",
        type=Path,
        help="Legacy direct odometry-directory override",
    )
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=1.0e-3)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="auto")
    parser.add_argument(
        "--resume",
        nargs="?",
        const="",
        metavar="CHECKPOINT",
        help=(f"Resume Stage 1 training; without CHECKPOINT, load <destination>/{STAGE1_LAST_FILENAME}"),
    )
    args = parser.parse_args()

    run_dir = ensure_run_dir(args.run_dir) if args.run_dir else None
    if run_dir is not None:
        for relative_path in ("exported/policy.pt", "exported/deployment.json"):
            if not (run_dir / relative_path).is_file():
                raise FileNotFoundError(
                    f"{run_dir / relative_path} is missing; Stage 1 policy and odometry must share one run"
                )
        output_dir = odometry_dir(run_dir)
        update_run_manifest(run_dir, stage=1, training_domain="simulation")
    else:
        output_dir = args.output_dir.expanduser().resolve()
    resume_path = _resolve_resume_path(args.resume, output_dir)

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    files = expand_patterns(args.data)
    train_files, validation_files, test_files = split_files(files, seed=args.seed)
    split_json = split_manifest_json(train_files, validation_files, test_files)
    split_path = output_dir / "split.json"
    if resume_path is not None:
        if not split_path.is_file():
            raise FileNotFoundError(f"Stage 1 resume split is missing: {split_path}")
        if json.loads(split_path.read_text(encoding="utf-8")) != json.loads(split_json):
            raise ValueError("Stage 1 resume train/validation/test split does not match the checkpoint run")
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        split_path.write_text(split_json, encoding="utf-8")

    train_trajectories = [load_trajectory(path, expected_source_prefix="sim") for path in train_files]
    validation_trajectories = [load_trajectory(path, expected_source_prefix="sim") for path in validation_files]
    train_dataset = Stage1WindowDataset(train_trajectories)
    validation_dataset = Stage1WindowDataset(validation_trajectories)
    if not train_dataset or not validation_dataset:
        raise ValueError("Each Stage 1 split needs at least one trajectory longer than 50 frames")

    manifest = trajectory_manifest(files)
    start_epoch = 0
    resume_checkpoint: dict[str, Any] | None = None
    if resume_path is not None:
        model, resume_checkpoint = load_checkpoint(
            resume_path,
            expected_stage=1,
            map_location="cpu",
        )
        start_epoch = _validate_resume_checkpoint(
            resume_checkpoint,
            data_manifest=manifest,
            seed=args.seed,
            total_epochs=args.epochs,
        )
        feature_mean = torch.as_tensor(resume_checkpoint["feature_mean"], dtype=torch.float32).cpu()
        feature_std = torch.as_tensor(resume_checkpoint["feature_std"], dtype=torch.float32).cpu()
        target_mean = torch.as_tensor(resume_checkpoint["target_mean"], dtype=torch.float32).cpu()
        target_std = torch.as_tensor(resume_checkpoint["target_std"], dtype=torch.float32).cpu()
    else:
        model = AutoOdomNet(input_dim=45)
        feature_mean, feature_std, target_mean, target_std = compute_stage1_statistics(
            train_dataset,
            seed=args.seed,
        )

    device = _device(args.device)
    feature_mean_device = feature_mean.to(device)
    feature_std_device = feature_std.to(device)
    generator = torch.Generator().manual_seed(args.seed)
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.workers,
        generator=generator,
    )
    validation_loader = DataLoader(
        validation_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
    )
    model.to(device)
    criterion = AutoOdomLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate, weight_decay=1.0e-5)
    if resume_checkpoint is not None:
        optimizer.load_state_dict(resume_checkpoint["optimizer_state_dict"])
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1.0e-6)
    scheduler_warning = None
    if resume_checkpoint is not None:
        scheduler_warning = _restore_scheduler(
            scheduler,
            resume_checkpoint,
            completed_epoch=start_epoch,
            total_epochs=args.epochs,
        )
        train_losses = list(resume_checkpoint["train_losses"])
        validation_losses = list(resume_checkpoint["validation_losses"])
        best_validation = float(resume_checkpoint["best_validation_loss"])
        rng_state = resume_checkpoint.get("rng_state")
        rng_warning = None
        if rng_state is not None:
            _restore_rng_state(rng_state, generator=generator, device=device)
        else:
            rng_warning = (
                "checkpoint predates RNG-state saving; model/optimizer/LR are restored, "
                "but shuffle/dropout will restart from the configured seed"
            )
    else:
        train_losses: list[float] = []
        validation_losses: list[float] = []
        best_validation = float("inf")
        rng_warning = None

    print(f"Stage 1: {len(train_dataset)} train / {len(validation_dataset)} validation windows on {device}")
    if resume_path is not None:
        print(f"[RESUME] {resume_path}: completed epoch {start_epoch}, continuing through epoch {args.epochs}")
        for warning in (scheduler_warning, rng_warning):
            if warning is not None:
                print(f"[WARN] {warning}")
    for epoch in range(start_epoch + 1, args.epochs + 1):
        train_loss = _average_loss(
            model,
            train_loader,
            criterion,
            feature_mean_device,
            feature_std_device,
            device,
            optimizer,
        )
        validation_loss = _average_loss(
            model,
            validation_loader,
            criterion,
            feature_mean_device,
            feature_std_device,
            device,
            None,
        )
        scheduler.step()
        train_losses.append(train_loss)
        validation_losses.append(validation_loss)
        is_best = validation_loss < best_validation
        if is_best:
            best_validation = validation_loss
        payload = checkpoint_payload(
            stage=1,
            epoch=epoch,
            model=model,
            optimizer=optimizer,
            feature_mean=feature_mean,
            feature_std=feature_std,
            target_mean=target_mean,
            target_std=target_std,
            best_validation_loss=best_validation,
            train_losses=train_losses,
            validation_losses=validation_losses,
            data_manifest=manifest,
        )
        payload.update({
            "scheduler_state_dict": scheduler.state_dict(),
            "training_config": {
                "epochs": args.epochs,
                "batch_size": args.batch_size,
                "learning_rate": optimizer.param_groups[0].get(
                    "initial_lr",
                    args.learning_rate,
                ),
                "workers": args.workers,
                "seed": args.seed,
            },
            "rng_state": _capture_rng_state(generator, device),
        })
        atomic_torch_save(payload, output_dir / STAGE1_LAST_FILENAME)
        if is_best:
            atomic_torch_save(payload, output_dir / STAGE1_BEST_FILENAME)
        print(
            f"epoch={epoch:04d} train={train_loss:.6f} validation={validation_loss:.6f} "
            f"lr={scheduler.get_last_lr()[0]:.2e}"
        )

    summary = {
        "best_validation_loss": best_validation,
        "train_files": len(train_files),
        "validation_files": len(validation_files),
        "test_files": len(test_files),
        "device": str(device),
        "training_domain": "simulation",
        "run_dir": str(run_dir) if run_dir is not None else None,
        "epochs": args.epochs,
        "resumed_from": str(resume_path) if resume_path is not None else None,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[SUCCESS] Stage 1 simulation odometry: {(output_dir / STAGE1_BEST_FILENAME).resolve()}")


if __name__ == "__main__":
    main()
