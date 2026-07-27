"""TorchScript locomotion policy runtime matching the Isaac Lab observation contract."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from ..constants import GO2_DEFAULT_JOINT_POS, LOCOMOTION_POLICY_OBS_DIM
from ..deployment import load_deployment_manifest
from ..math_utils import projected_gravity_from_wxyz
from ..policy_quality import validate_policy_actions
from .low_level import Go2State


class Go2LocomotionPolicy:
    def __init__(self, deployment_json: str | Path, device: str | torch.device = "cpu"):
        deployment_json = Path(deployment_json).expanduser().resolve()
        self.manifest = load_deployment_manifest(deployment_json)
        policy_path = (deployment_json.parent / str(self.manifest["policy_file"])).resolve()
        if policy_path.parent != deployment_json.parent:
            raise ValueError("policy_file must be located beside deployment.json")
        if not policy_path.is_file():
            raise FileNotFoundError(policy_path)
        self.device = torch.device(device)
        self.module = torch.jit.load(str(policy_path), map_location=self.device)
        self.module.eval()
        self.previous_action = np.zeros(12, dtype=np.float32)

    def reset(self) -> None:
        self.previous_action.fill(0.0)

    def observation(self, state: Go2State, command: np.ndarray) -> np.ndarray:
        observation = np.concatenate([
            state.gyro,
            projected_gravity_from_wxyz(state.quaternion_wxyz),
            np.asarray(command, dtype=np.float32).reshape(3),
            state.joint_pos - GO2_DEFAULT_JOINT_POS,
            state.joint_vel,
            self.previous_action,
        ]).astype(np.float32)
        if observation.shape != (LOCOMOTION_POLICY_OBS_DIM,) or not np.isfinite(observation).all():
            raise RuntimeError(f"Invalid Go2 locomotion observation: shape={observation.shape}")
        return observation

    def act(self, state: Go2State, command: np.ndarray) -> np.ndarray:
        observation = torch.from_numpy(self.observation(state, command)).unsqueeze(0).to(self.device)
        with torch.inference_mode():
            output = self.module(observation)
        if isinstance(output, (tuple, list)):
            output = output[0]
        output = torch.as_tensor(output)
        validate_policy_actions(output, context="Locomotion policy")
        action = output.detach().cpu().numpy().reshape(12).astype(np.float32)
        self.previous_action = action.copy()
        return action.copy()
