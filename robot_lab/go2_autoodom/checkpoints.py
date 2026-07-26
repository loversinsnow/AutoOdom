"""Checkpoint provenance and strict model loading."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import torch

from .constants import (
    AUTOODOM_STAGE1_DIM,
    AUTOODOM_STAGE1_FEATURES,
    AUTOODOM_STAGE2_DIM,
    AUTOODOM_STAGE2_FEATURES,
    DATA_FORMAT_VERSION,
    GO2_JOINT_NAMES,
    HISTORY_LENGTH,
)
from .model import AutoOdomNet, model_from_config


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checkpoint_payload(
    *,
    stage: int,
    epoch: int,
    model: AutoOdomNet,
    optimizer: torch.optim.Optimizer | None,
    feature_mean: torch.Tensor,
    feature_std: torch.Tensor,
    target_mean: torch.Tensor,
    target_std: torch.Tensor,
    best_validation_loss: float,
    train_losses: list[float],
    validation_losses: list[float],
    data_manifest: str,
    parent_stage1_sha256: str | None = None,
) -> dict[str, Any]:
    expected_dim = AUTOODOM_STAGE1_DIM if stage == 1 else AUTOODOM_STAGE2_DIM
    if model.input_dim != expected_dim:
        raise ValueError(f"Stage {stage} checkpoint must use input_dim={expected_dim}, got {model.input_dim}")
    return {
        "format_version": 1,
        "data_format_version": DATA_FORMAT_VERSION,
        "stage": stage,
        "training_domain": "simulation" if stage == 1 else "real",
        "epoch": int(epoch),
        "model_config": model.config(),
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict() if optimizer is not None else None,
        "feature_mean": feature_mean.detach().cpu(),
        "feature_std": feature_std.detach().cpu(),
        "target_mean": target_mean.detach().cpu(),
        "target_std": target_std.detach().cpu(),
        "best_validation_loss": float(best_validation_loss),
        "train_losses": list(train_losses),
        "validation_losses": list(validation_losses),
        "history_length": HISTORY_LENGTH,
        "joint_names": GO2_JOINT_NAMES,
        "feature_order": AUTOODOM_STAGE1_FEATURES if stage == 1 else AUTOODOM_STAGE2_FEATURES,
        "data_manifest_sha256": data_manifest,
        "parent_stage1_sha256": parent_stage1_sha256,
    }


def load_checkpoint(
    path: str | Path,
    *,
    expected_stage: int | None = None,
    map_location: str | torch.device = "cpu",
) -> tuple[AutoOdomNet, dict[str, Any]]:
    path = Path(path).expanduser().resolve()
    checkpoint = torch.load(path, map_location=map_location, weights_only=False)
    if "model_config" not in checkpoint or "model_state_dict" not in checkpoint:
        raise ValueError(
            f"{path} is not a Go2 AutoOdom checkpoint. Legacy Booster checkpoints cannot be used with 12-DOF Go2."
        )
    stage = int(checkpoint.get("stage", 0))
    if expected_stage is not None and stage != expected_stage:
        raise ValueError(f"{path} is Stage {stage}, expected Stage {expected_stage}")
    expected_domain = "simulation" if stage == 1 else "real"
    training_domain = checkpoint.get("training_domain", expected_domain)
    if training_domain != expected_domain:
        raise ValueError(
            f"{path} has training_domain={training_domain!r}; Stage {stage} requires {expected_domain!r}"
        )
    if tuple(checkpoint.get("joint_names", ())) != GO2_JOINT_NAMES:
        raise ValueError(f"{path} does not use the canonical Go2 joint order")
    expected_dim = AUTOODOM_STAGE1_DIM if stage == 1 else AUTOODOM_STAGE2_DIM
    if int(checkpoint["model_config"]["input_dim"]) != expected_dim:
        raise ValueError(f"{path} has an invalid Stage {stage} input dimension")
    model = model_from_config(checkpoint["model_config"])
    model.load_state_dict(checkpoint["model_state_dict"])
    return model, checkpoint
