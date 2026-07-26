"""Small, dependency-light rotation helpers shared by simulation and real code."""

from __future__ import annotations

import numpy as np


def normalize_quaternion_wxyz(quaternion: np.ndarray) -> np.ndarray:
    quaternion = np.asarray(quaternion, dtype=np.float64).reshape(4)
    norm = float(np.linalg.norm(quaternion))
    if norm <= 1.0e-12:
        raise ValueError("Quaternion norm must be positive.")
    return quaternion / norm


def rotation_matrix_from_wxyz(quaternion: np.ndarray) -> np.ndarray:
    """Return the world-from-body rotation matrix for a wxyz quaternion."""
    w, x, y, z = normalize_quaternion_wxyz(quaternion)
    return np.asarray(
        [
            [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)],
            [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
            [2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)],
        ],
        dtype=np.float32,
    )


def projected_gravity_from_wxyz(quaternion: np.ndarray) -> np.ndarray:
    """Express the unit world gravity vector in the body frame."""
    world_from_body = rotation_matrix_from_wxyz(quaternion)
    return (world_from_body.T @ np.asarray([0.0, 0.0, -1.0], dtype=np.float32)).astype(np.float32)


def legacy_gravity_feature(rotation_matrices: np.ndarray) -> np.ndarray:
    """Preserve the original Stage 1 feature extraction (third rotation column)."""
    matrices = np.asarray(rotation_matrices, dtype=np.float32)
    if matrices.ndim != 3 or matrices.shape[1:] != (3, 3):
        raise ValueError(f"base_rot_mat must have shape (T, 3, 3), got {matrices.shape}")
    return matrices[:, :, 2]


def local_increment(previous_world: np.ndarray, current_world: np.ndarray, world_from_body: np.ndarray) -> np.ndarray:
    delta_world = np.asarray(current_world, dtype=np.float32) - np.asarray(previous_world, dtype=np.float32)
    return (np.asarray(world_from_body, dtype=np.float32).T @ delta_world).astype(np.float32)
