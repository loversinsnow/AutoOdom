"""Shared checks for obviously degenerate locomotion-policy outputs."""

from __future__ import annotations

from dataclasses import dataclass

import torch


POLICY_ACTION_DIM = 12
MAX_RAW_POLICY_ACTION = 10.0


@dataclass(frozen=True)
class PolicyActionStats:
    max_abs: float
    outside_unit_range_fraction: float


def validate_policy_actions(actions: torch.Tensor, *, context: str) -> PolicyActionStats:
    """Reject non-finite, malformed, or grossly divergent raw policy actions."""
    tensor = torch.as_tensor(actions)
    if tensor.ndim < 1 or tensor.shape[-1] != POLICY_ACTION_DIM:
        raise RuntimeError(f"{context} produced actions with shape {tuple(tensor.shape)}; expected (..., 12)")
    if tensor.numel() == 0:
        raise RuntimeError(f"{context} produced an empty action tensor")
    if not bool(torch.isfinite(tensor).all()):
        raise RuntimeError(f"{context} produced NaN or infinity")

    absolute = tensor.detach().abs()
    max_abs = float(absolute.max().item())
    outside_unit_range_fraction = float((absolute > 1.0).to(dtype=torch.float32).mean().item())
    if max_abs > MAX_RAW_POLICY_ACTION:
        raise RuntimeError(
            f"{context} produced a degenerate raw action (max |action|={max_abs:.3f}, "
            f"safety limit={MAX_RAW_POLICY_ACTION:.1f}). This commonly happens when PPO is trained behind "
            "hard action clipping. Retrain the locomotion policy before collection, evaluation, or real control."
        )
    return PolicyActionStats(
        max_abs=max_abs,
        outside_unit_range_fraction=outside_unit_range_fraction,
    )
