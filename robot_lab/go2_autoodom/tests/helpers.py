from __future__ import annotations

from pathlib import Path

import numpy as np

from go2_autoodom.constants import GO2_JOINT_NAMES, SAMPLE_DT
from go2_autoodom.data import Trajectory


def trajectory(length: int = 8, *, target_offset: float = 0.0, source: str = "real_go2_mocap") -> Trajectory:
    zeros12 = np.zeros((length, 12), dtype=np.float32)
    zeros3 = np.zeros((length, 3), dtype=np.float32)
    rotations = np.repeat(np.eye(3, dtype=np.float32)[None, ...], length, axis=0)
    targets = np.full((length, 3), target_offset, dtype=np.float32)
    positions = np.cumsum(targets, axis=0)
    return Trajectory(
        path=Path(f"trajectory_{target_offset}.npz"),
        joint_pos=zeros12.copy(),
        joint_vel=zeros12.copy(),
        joint_commands=zeros12.copy(),
        gyro_ang_vel=zeros3.copy(),
        imu_lin_acc=zeros3.copy(),
        base_rot_mat=rotations,
        cmd_vel=zeros3.copy(),
        pos_increment_hist=targets,
        root_pos_abs=positions,
        sample_dt=SAMPLE_DT,
        source=source,
        data_version="go2-autoodom-v1",
    )


def valid_arrays(length: int = 60) -> dict[str, np.ndarray]:
    return {
        "joint_pos": np.zeros((length, len(GO2_JOINT_NAMES)), dtype=np.float32),
        "joint_vel": np.zeros((length, len(GO2_JOINT_NAMES)), dtype=np.float32),
        "joint_commands": np.zeros((length, len(GO2_JOINT_NAMES)), dtype=np.float32),
        "gyro_ang_vel": np.zeros((length, 3), dtype=np.float32),
        "imu_lin_acc": np.zeros((length, 3), dtype=np.float32),
        "base_rot_mat": np.repeat(np.eye(3, dtype=np.float32)[None, ...], length, axis=0),
        "cmd_vel": np.zeros((length, 3), dtype=np.float32),
        "pos_increment_hist": np.zeros((length, 3), dtype=np.float32),
        "root_pos_abs": np.zeros((length, 3), dtype=np.float32),
    }
