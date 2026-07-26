"""Trajectory reconstruction and odometry metrics."""

from __future__ import annotations

import numpy as np


def integrate_local_increments(local_increments: np.ndarray, world_from_body: np.ndarray) -> np.ndarray:
    local_increments = np.asarray(local_increments, dtype=np.float64)
    rotations = np.asarray(world_from_body, dtype=np.float64)
    if local_increments.ndim != 2 or local_increments.shape[1] != 3:
        raise ValueError("local_increments must have shape (T, 3)")
    if rotations.shape != (local_increments.shape[0], 3, 3):
        raise ValueError("world_from_body must have shape (T, 3, 3)")
    world_steps = np.einsum("tij,tj->ti", rotations, local_increments)
    positions = np.zeros_like(world_steps)
    if len(positions) > 1:
        positions[1:] = np.cumsum(world_steps[1:], axis=0)
    return positions


def umeyama_align(source: np.ndarray, target: np.ndarray, *, with_scale: bool = False) -> np.ndarray:
    source = np.asarray(source, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    if source.shape != target.shape or source.ndim != 2 or source.shape[1] != 3:
        raise ValueError("source and target must both have shape (T, 3)")
    source_mean = source.mean(axis=0)
    target_mean = target.mean(axis=0)
    source_centered = source - source_mean
    target_centered = target - target_mean
    covariance = target_centered.T @ source_centered / float(len(source))
    left, singular_values, right_transpose = np.linalg.svd(covariance)
    correction = np.eye(3)
    if np.linalg.det(left) * np.linalg.det(right_transpose) < 0.0:
        correction[-1, -1] = -1.0
    rotation = left @ correction @ right_transpose
    scale = 1.0
    if with_scale:
        variance = np.mean(np.sum(source_centered**2, axis=1))
        if variance > 1.0e-12:
            scale = float(np.sum(singular_values * np.diag(correction)) / variance)
    translation = target_mean - scale * rotation @ source_mean
    return (scale * (rotation @ source.T)).T + translation


def trajectory_metrics(
    predicted_local: np.ndarray,
    target_local: np.ndarray,
    rotations: np.ndarray,
    target_world: np.ndarray,
) -> dict[str, float]:
    predicted_local = np.asarray(predicted_local, dtype=np.float64)
    target_local = np.asarray(target_local, dtype=np.float64)
    target_world = np.asarray(target_world, dtype=np.float64)
    predicted_world = integrate_local_increments(predicted_local, rotations)
    target_world_aligned_origin = target_world - target_world[0]

    step_error = predicted_local - target_local
    world_error = predicted_world - target_world_aligned_origin
    umeyama_prediction = umeyama_align(predicted_world, target_world_aligned_origin, with_scale=False)
    path_length = float(np.linalg.norm(np.diff(target_world_aligned_origin, axis=0), axis=1).sum())
    final_drift = float(np.linalg.norm(world_error[-1]))
    return {
        "step_rmse": float(np.sqrt(np.mean(step_error**2))),
        "rpe_translation": float(
            np.sqrt(
                np.mean(
                    np.sum(
                        (np.diff(predicted_world, axis=0) - np.diff(target_world_aligned_origin, axis=0)) ** 2,
                        axis=1,
                    )
                )
            )
        ),
        "ate_origin": float(np.sqrt(np.mean(np.sum(world_error**2, axis=1)))),
        "ate_umeyama": float(
            np.sqrt(np.mean(np.sum((umeyama_prediction - target_world_aligned_origin) ** 2, axis=1)))
        ),
        "final_drift": final_drift,
        "relative_final_drift": final_drift / max(path_length, 1.0e-8),
        "path_length": path_length,
    }
