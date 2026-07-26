"""Strict Go2 trajectory schema and AutoOdom feature construction."""

from __future__ import annotations

import glob
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import torch
from torch.utils.data import Dataset

from .constants import (
    AUTOODOM_STAGE1_DIM,
    AUTOODOM_STAGE2_DIM,
    DATA_FORMAT_VERSION,
    GO2_JOINT_NAMES,
    HISTORY_LENGTH,
    SAMPLE_DT,
)
from .math_utils import legacy_gravity_feature


REQUIRED_ARRAYS = {
    "joint_pos": (12,),
    "joint_vel": (12,),
    "joint_commands": (12,),
    "gyro_ang_vel": (3,),
    "base_rot_mat": (3, 3),
    "cmd_vel": (3,),
    "pos_increment_hist": (3,),
    "root_pos_abs": (3,),
}


class DataContractError(ValueError):
    """Raised when a trajectory is not a continuous Go2 AutoOdom recording."""


def _string_scalar(value: np.ndarray | str | object, default: str = "") -> str:
    if value is None:
        return default
    array = np.asarray(value)
    if array.size == 0:
        return default
    item = array.reshape(-1)[0]
    if isinstance(item, bytes):
        return item.decode("utf-8")
    return str(item)


@dataclass(frozen=True)
class Trajectory:
    path: Path
    joint_pos: np.ndarray
    joint_vel: np.ndarray
    joint_commands: np.ndarray
    gyro_ang_vel: np.ndarray
    imu_lin_acc: np.ndarray
    base_rot_mat: np.ndarray
    cmd_vel: np.ndarray
    pos_increment_hist: np.ndarray
    root_pos_abs: np.ndarray
    sample_dt: float
    source: str
    data_version: str
    mocap_rot_mat: np.ndarray | None = None

    @property
    def length(self) -> int:
        return int(self.joint_pos.shape[0])

    @property
    def gravity_vec(self) -> np.ndarray:
        return legacy_gravity_feature(self.base_rot_mat)

    @property
    def static_features(self) -> np.ndarray:
        """The 42 non-autoregressive Stage 1 channels."""
        return np.concatenate(
            [
                self.joint_pos,
                self.joint_vel,
                self.gyro_ang_vel,
                self.gravity_vec,
                self.joint_commands,
            ],
            axis=1,
        ).astype(np.float32, copy=False)


def expand_patterns(patterns: Sequence[str]) -> list[Path]:
    """Expand path/glob arguments deterministically and reject duplicates."""
    files: list[Path] = []
    for pattern in patterns:
        matches = [Path(path) for path in glob.glob(str(Path(pattern).expanduser()))]
        if not matches and Path(pattern).expanduser().is_file():
            matches = [Path(pattern).expanduser()]
        files.extend(matches)
    unique = sorted({path.resolve() for path in files})
    if not unique:
        raise FileNotFoundError(f"No trajectory files matched: {list(patterns)}")
    return unique


def load_trajectory(
    path: str | Path,
    *,
    require_acceleration: bool = False,
    expected_source_prefix: str | None = None,
) -> Trajectory:
    """Load a trajectory and reject Booster/incorrectly ordered data."""
    path = Path(path).expanduser().resolve()
    try:
        archive = np.load(path, allow_pickle=False)
    except Exception as exc:
        raise DataContractError(f"Cannot load {path}: {exc}") from exc

    with archive:
        missing = sorted(set(REQUIRED_ARRAYS) - set(archive.files))
        if missing:
            raise DataContractError(f"{path}: missing required arrays: {', '.join(missing)}")

        arrays: dict[str, np.ndarray] = {}
        length: int | None = None
        for name, trailing_shape in REQUIRED_ARRAYS.items():
            array = np.asarray(archive[name], dtype=np.float32)
            if array.ndim != len(trailing_shape) + 1 or array.shape[1:] != trailing_shape:
                raise DataContractError(
                    f"{path}: {name} must have shape (T, {', '.join(map(str, trailing_shape))}), got {array.shape}"
                )
            length = array.shape[0] if length is None else length
            if array.shape[0] != length:
                raise DataContractError(f"{path}: arrays do not share one trajectory length")
            if not np.isfinite(array).all():
                raise DataContractError(f"{path}: {name} contains NaN or infinity")
            arrays[name] = array

        if length is None or length < 2:
            raise DataContractError(f"{path}: trajectory must contain at least two frames")

        if "joint_names" not in archive.files:
            raise DataContractError(f"{path}: joint_names is required to verify canonical Go2 ordering")
        joint_names = tuple(str(item) for item in np.asarray(archive["joint_names"]).tolist())
        if joint_names != GO2_JOINT_NAMES:
            raise DataContractError(
                f"{path}: expected canonical Go2 joint_names {GO2_JOINT_NAMES}, got {joint_names}; "
                "23-DOF Booster data is intentionally unsupported"
            )

        if "imu_lin_acc" in archive.files:
            acceleration = np.asarray(archive["imu_lin_acc"], dtype=np.float32)
            if acceleration.shape != (length, 3) or not np.isfinite(acceleration).all():
                raise DataContractError(f"{path}: imu_lin_acc must be finite with shape ({length}, 3)")
        elif require_acceleration:
            raise DataContractError(f"{path}: Stage 2 requires imu_lin_acc with shape (T, 3)")
        else:
            acceleration = np.zeros((length, 3), dtype=np.float32)

        sample_dt = (
            float(np.asarray(archive["sample_dt"]).reshape(-1)[0])
            if "sample_dt" in archive.files
            else SAMPLE_DT
        )
        if not np.isfinite(sample_dt) or abs(sample_dt - SAMPLE_DT) > 1.0e-4:
            raise DataContractError(f"{path}: sample_dt must be {SAMPLE_DT:.2f}s (50 Hz), got {sample_dt}")

        source = _string_scalar(archive["source"] if "source" in archive.files else None, "unknown")
        if expected_source_prefix and not source.startswith(expected_source_prefix):
            raise DataContractError(
                f"{path}: expected source beginning with {expected_source_prefix!r}, got {source!r}"
            )
        data_version = _string_scalar(
            archive["data_version"] if "data_version" in archive.files else None,
            DATA_FORMAT_VERSION,
        )
        mocap_rotation = None
        if "mocap_rot_mat" in archive.files:
            mocap_rotation = np.asarray(archive["mocap_rot_mat"], dtype=np.float32)
            if mocap_rotation.shape != (length, 3, 3) or not np.isfinite(mocap_rotation).all():
                raise DataContractError(
                    f"{path}: mocap_rot_mat must be finite with shape ({length}, 3, 3)"
                )

    return Trajectory(
        path=path,
        imu_lin_acc=acceleration,
        sample_dt=sample_dt,
        source=source,
        data_version=data_version,
        mocap_rot_mat=mocap_rotation,
        **arrays,
    )


def save_trajectory(path: str | Path, arrays: dict[str, np.ndarray], *, source: str) -> Path:
    """Validate and save one trajectory using the repository data contract."""
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **arrays,
        "joint_names": np.asarray(GO2_JOINT_NAMES),
        "sample_dt": np.asarray(SAMPLE_DT, dtype=np.float32),
        "source": np.asarray(source),
        "data_version": np.asarray(DATA_FORMAT_VERSION),
    }
    np.savez_compressed(path, **payload)
    # Re-open immediately so a collector cannot silently produce unusable training data.
    load_trajectory(path, require_acceleration=True)
    return path.resolve()


def trajectory_manifest(files: Iterable[str | Path]) -> str:
    entries = []
    for path_like in sorted(Path(path).resolve() for path in files):
        stat = path_like.stat()
        entries.append(f"{path_like.name}:{stat.st_size}:{stat.st_mtime_ns}")
    return hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest()


def split_files(
    files: Sequence[str | Path],
    *,
    seed: int = 42,
    fractions: tuple[float, float, float] = (0.70, 0.15, 0.15),
) -> tuple[list[Path], list[Path], list[Path]]:
    """Split whole trajectory files, never windows from the same file."""
    if len(fractions) != 3 or not np.isclose(sum(fractions), 1.0):
        raise ValueError("fractions must contain train/validation/test values that sum to 1")
    ordered = sorted(Path(path).resolve() for path in files)
    if len(ordered) < 3:
        raise ValueError("At least three trajectory files are required for leakage-free train/val/test splits")
    rng = np.random.default_rng(seed)
    shuffled = [ordered[index] for index in rng.permutation(len(ordered))]
    train_count = max(1, int(np.floor(len(shuffled) * fractions[0])))
    val_count = max(1, int(np.floor(len(shuffled) * fractions[1])))
    if train_count + val_count >= len(shuffled):
        train_count = len(shuffled) - 2
        val_count = 1
    return (
        shuffled[:train_count],
        shuffled[train_count : train_count + val_count],
        shuffled[train_count + val_count :],
    )


def frame_features(
    trajectory: Trajectory,
    time_index: int,
    previous_increment: np.ndarray,
    *,
    stage: int,
) -> np.ndarray:
    previous_increment = np.asarray(previous_increment, dtype=np.float32).reshape(3)
    features = np.concatenate([trajectory.static_features[time_index], previous_increment])
    if stage == 2:
        features = np.concatenate([features, trajectory.imu_lin_acc[time_index]])
    expected = AUTOODOM_STAGE1_DIM if stage == 1 else AUTOODOM_STAGE2_DIM
    if features.shape != (expected,):
        raise RuntimeError(f"Internal feature construction error: expected {expected}, got {features.shape}")
    return features.astype(np.float32, copy=False)


class Stage1WindowDataset(Dataset):
    """The existing Stage 1 teacher-feedback window semantics, adapted from 23 to 12 joints."""

    def __init__(self, trajectories: Sequence[Trajectory], history_length: int = HISTORY_LENGTH):
        self.trajectories = list(trajectories)
        self.history_length = int(history_length)
        self.sample_indices: list[tuple[int, int]] = []
        for trajectory_index, trajectory in enumerate(self.trajectories):
            # Preserve the original implementation's T-history count and final-frame omission.
            for start in range(max(0, trajectory.length - self.history_length)):
                self.sample_indices.append((trajectory_index, start))

    def __len__(self) -> int:
        return len(self.sample_indices)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        trajectory_index, start = self.sample_indices[index]
        trajectory = self.trajectories[trajectory_index]
        frames = []
        for time_index in range(start, start + self.history_length):
            previous = (
                trajectory.pos_increment_hist[time_index - 1]
                if time_index > 0
                else np.zeros(3, dtype=np.float32)
            )
            frames.append(frame_features(trajectory, time_index, previous, stage=1))
        target_index = start + self.history_length - 1
        return (
            torch.from_numpy(np.stack(frames)),
            torch.from_numpy(trajectory.pos_increment_hist[target_index].copy()),
        )


def compute_stage1_statistics(
    dataset: Stage1WindowDataset,
    *,
    seed: int = 42,
    max_samples: int = 50_000,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    if not dataset:
        raise ValueError("Cannot compute normalization statistics from an empty dataset")
    rng = np.random.default_rng(seed)
    count = min(max_samples, len(dataset))
    indices = rng.choice(len(dataset), size=count, replace=False)
    features = []
    targets = []
    for sample_index in indices:
        trajectory_index, start = dataset.sample_indices[int(sample_index)]
        trajectory = dataset.trajectories[trajectory_index]
        time_index = start + dataset.history_length - 1
        previous = (
            trajectory.pos_increment_hist[time_index - 1]
            if time_index > 0
            else np.zeros(3, dtype=np.float32)
        )
        features.append(frame_features(trajectory, time_index, previous, stage=1))
        targets.append(trajectory.pos_increment_hist[time_index])
    feature_array = np.stack(features).astype(np.float32)
    target_array = np.stack(targets).astype(np.float32)
    return (
        torch.from_numpy(feature_array.mean(axis=0)),
        torch.from_numpy(feature_array.std(axis=0) + 1.0e-8),
        torch.from_numpy(target_array.mean(axis=0)),
        torch.from_numpy(target_array.std(axis=0) + 1.0e-8),
    )


def split_manifest_json(train: Sequence[Path], validation: Sequence[Path], test: Sequence[Path]) -> str:
    return json.dumps(
        {
            "train": [path.name for path in train],
            "validation": [path.name for path in validation],
            "test": [path.name for path in test],
        },
        indent=2,
        sort_keys=True,
    )
