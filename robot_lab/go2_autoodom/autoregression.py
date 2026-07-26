"""Closed-loop inference and Stage 2 sequence training without label feedback."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np
import torch
from torch import nn

from .constants import AUTOODOM_STAGE1_DIM, AUTOODOM_STAGE2_DIM, HISTORY_LENGTH
from .data import Trajectory, frame_features


@dataclass
class RolloutResult:
    predictions: np.ndarray
    mse: float


def _normalization_arrays(
    feature_mean: torch.Tensor | np.ndarray,
    feature_std: torch.Tensor | np.ndarray,
    expected_dim: int,
) -> tuple[np.ndarray, np.ndarray]:
    mean = np.asarray(torch.as_tensor(feature_mean).cpu(), dtype=np.float32).reshape(-1)
    std = np.asarray(torch.as_tensor(feature_std).cpu(), dtype=np.float32).reshape(-1)
    if mean.shape != (expected_dim,) or std.shape != (expected_dim,):
        raise ValueError(f"Expected normalization vectors of length {expected_dim}, got {mean.shape} and {std.shape}")
    if np.any(std <= 0.0):
        raise ValueError("All normalization standard deviations must be positive")
    return mean, std


def rollout_closed_loop(
    model: nn.Module,
    trajectory: Trajectory,
    feature_mean: torch.Tensor | np.ndarray,
    feature_std: torch.Tensor | np.ndarray,
    *,
    stage: int,
    device: torch.device | str,
    history_length: int = HISTORY_LENGTH,
) -> RolloutResult:
    """Predict an entire trajectory using only previous model predictions.

    The history is left-padded with raw zeros. Ground-truth increments are used
    only for the final MSE calculation and never enter the feature buffer.
    """
    expected_dim = AUTOODOM_STAGE1_DIM if stage == 1 else AUTOODOM_STAGE2_DIM
    mean, std = _normalization_arrays(feature_mean, feature_std, expected_dim)
    window: deque[np.ndarray] = deque(
        [np.zeros(expected_dim, dtype=np.float32) for _ in range(history_length - 1)],
        maxlen=history_length,
    )
    previous_prediction = np.zeros(3, dtype=np.float32)
    predictions = np.zeros((trajectory.length, 3), dtype=np.float32)
    model.eval()
    with torch.no_grad():
        for time_index in range(trajectory.length):
            # This call receives only previous_prediction; no target is visible.
            window.append(frame_features(trajectory, time_index, previous_prediction, stage=stage))
            normalized = (np.stack(window) - mean) / std
            inputs = torch.from_numpy(normalized).unsqueeze(0).to(device)
            prediction = model(inputs).detach().cpu().numpy().reshape(3).astype(np.float32)
            predictions[time_index] = prediction
            previous_prediction = prediction
    mse = float(np.mean((predictions - trajectory.pos_increment_hist) ** 2))
    return RolloutResult(predictions=predictions, mse=mse)


def rollout_stage1_legacy(
    model: nn.Module,
    trajectory: Trajectory,
    feature_mean: torch.Tensor | np.ndarray,
    feature_std: torch.Tensor | np.ndarray,
    *,
    device: torch.device | str,
    history_length: int = HISTORY_LENGTH,
) -> RolloutResult:
    """Preserve the original Stage 1 recursive evaluator's GT warm-up."""
    mean, std = _normalization_arrays(feature_mean, feature_std, AUTOODOM_STAGE1_DIM)
    predictions = np.zeros((trajectory.length, 3), dtype=np.float32)
    window: deque[np.ndarray] = deque(maxlen=history_length)
    warmup = min(history_length, trajectory.length)
    for time_index in range(warmup):
        previous = (
            trajectory.pos_increment_hist[time_index - 1]
            if time_index > 0
            else np.zeros(3, dtype=np.float32)
        )
        window.append(frame_features(trajectory, time_index, previous, stage=1))
        predictions[time_index] = trajectory.pos_increment_hist[time_index]

    model.eval()
    with torch.no_grad():
        for time_index in range(warmup, trajectory.length):
            previous = predictions[time_index - 1]
            window.append(frame_features(trajectory, time_index, previous, stage=1))
            normalized = (np.stack(window) - mean) / std
            inputs = torch.from_numpy(normalized).unsqueeze(0).to(device)
            predictions[time_index] = model(inputs).detach().cpu().numpy().reshape(3)
    mse = float(np.mean((predictions - trajectory.pos_increment_hist) ** 2))
    return RolloutResult(predictions=predictions, mse=mse)


def train_stage2_trajectory(
    model: nn.Module,
    trajectory: Trajectory,
    feature_mean: torch.Tensor | np.ndarray,
    feature_std: torch.Tensor | np.ndarray,
    optimizer: torch.optim.Optimizer,
    *,
    device: torch.device | str,
    history_length: int = HISTORY_LENGTH,
    chunk_size: int = 64,
    max_grad_norm: float = 1.0,
) -> RolloutResult:
    """Fine-tune on one real trajectory with detached self-prediction feedback."""
    mean, std = _normalization_arrays(feature_mean, feature_std, AUTOODOM_STAGE2_DIM)
    window: deque[np.ndarray] = deque(
        [np.zeros(AUTOODOM_STAGE2_DIM, dtype=np.float32) for _ in range(history_length - 1)],
        maxlen=history_length,
    )
    previous_prediction = np.zeros(3, dtype=np.float32)
    predictions = np.zeros((trajectory.length, 3), dtype=np.float32)
    pending_losses: list[torch.Tensor] = []
    squared_error_sum = 0.0
    model.train()
    optimizer.zero_grad(set_to_none=True)

    for time_index in range(trajectory.length):
        window.append(frame_features(trajectory, time_index, previous_prediction, stage=2))
        normalized = (np.stack(window) - mean) / std
        inputs = torch.from_numpy(normalized).unsqueeze(0).to(device)
        target = torch.from_numpy(trajectory.pos_increment_hist[time_index]).unsqueeze(0).to(device)
        prediction = model(inputs)
        loss = nn.functional.mse_loss(prediction, target)
        pending_losses.append(loss)
        detached_prediction = prediction.detach().cpu().numpy().reshape(3).astype(np.float32)
        predictions[time_index] = detached_prediction
        # Explicit detach: gradients cannot cross the autoregressive feedback edge.
        previous_prediction = detached_prediction
        squared_error_sum += float(torch.sum((prediction.detach() - target) ** 2).cpu())

        is_chunk_end = len(pending_losses) >= chunk_size or time_index == trajectory.length - 1
        if is_chunk_end:
            torch.stack(pending_losses).mean().backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            pending_losses.clear()

    return RolloutResult(
        predictions=predictions,
        mse=squared_error_sum / float(trajectory.length * 3),
    )
