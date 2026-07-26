"""Online AutoOdom inference with no mocap or ground-truth dependency."""

from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
import torch

from .checkpoints import load_checkpoint
from .constants import AUTOODOM_STAGE1_DIM, AUTOODOM_STAGE2_DIM, HISTORY_LENGTH
from .math_utils import legacy_gravity_feature


class OnlineAutoOdom:
    """Stateful 50-frame estimator for deployment on Go2."""

    def __init__(self, checkpoint_path: str | Path, device: str | torch.device = "cpu"):
        self.device = torch.device(device)
        self.model, self.checkpoint = load_checkpoint(checkpoint_path, map_location=self.device)
        self.model.to(self.device).eval()
        self.stage = int(self.checkpoint["stage"])
        self.input_dim = AUTOODOM_STAGE1_DIM if self.stage == 1 else AUTOODOM_STAGE2_DIM
        self.mean = torch.as_tensor(self.checkpoint["feature_mean"], dtype=torch.float32, device=self.device)
        self.std = torch.as_tensor(self.checkpoint["feature_std"], dtype=torch.float32, device=self.device)
        if self.mean.shape != (self.input_dim,) or self.std.shape != (self.input_dim,):
            raise ValueError("Checkpoint normalization does not match its input dimension")
        self.reset()

    def reset(self) -> None:
        self.window: deque[np.ndarray] = deque(
            [np.zeros(self.input_dim, dtype=np.float32) for _ in range(HISTORY_LENGTH - 1)],
            maxlen=HISTORY_LENGTH,
        )
        self.previous_prediction = np.zeros(3, dtype=np.float32)
        self.world_position = np.zeros(3, dtype=np.float32)

    def update(
        self,
        *,
        joint_pos: np.ndarray,
        joint_vel: np.ndarray,
        gyro_ang_vel: np.ndarray,
        base_rot_mat: np.ndarray,
        joint_commands: np.ndarray,
        imu_lin_acc: np.ndarray | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        rotation = np.asarray(base_rot_mat, dtype=np.float32).reshape(3, 3)
        gravity = legacy_gravity_feature(rotation[None, ...])[0]
        feature = np.concatenate(
            [
                np.asarray(joint_pos, dtype=np.float32).reshape(12),
                np.asarray(joint_vel, dtype=np.float32).reshape(12),
                np.asarray(gyro_ang_vel, dtype=np.float32).reshape(3),
                gravity,
                np.asarray(joint_commands, dtype=np.float32).reshape(12),
                self.previous_prediction,
            ]
        )
        if self.stage == 2:
            if imu_lin_acc is None:
                raise ValueError("Stage 2 online inference requires imu_lin_acc")
            feature = np.concatenate([feature, np.asarray(imu_lin_acc, dtype=np.float32).reshape(3)])
        if not np.isfinite(feature).all():
            raise ValueError("Online AutoOdom input contains NaN or infinity")
        self.window.append(feature.astype(np.float32))
        inputs = torch.from_numpy(np.stack(self.window)).unsqueeze(0).to(self.device)
        inputs = (inputs - self.mean) / self.std
        with torch.inference_mode():
            prediction = self.model(inputs).cpu().numpy().reshape(3).astype(np.float32)
        self.previous_prediction = prediction
        self.world_position = self.world_position + rotation @ prediction
        return prediction.copy(), self.world_position.copy()
