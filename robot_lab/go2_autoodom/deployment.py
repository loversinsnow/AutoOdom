"""Deployment manifest shared by policy export and real control."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .constants import (
    GO2_ACTION_SCALE,
    GO2_DDS_MOTOR_INDICES,
    GO2_DEFAULT_JOINT_POS,
    GO2_D_GAINS,
    GO2_JOINT_NAMES,
    GO2_P_GAINS,
    LOCOMOTION_POLICY_FEATURES,
    LOCOMOTION_POLICY_OBS_DIM,
    SAMPLE_DT,
)
from .policy_quality import MAX_RAW_POLICY_ACTION


def deployment_manifest(policy_file: str = "policy.pt") -> dict[str, object]:
    return {
        "format_version": 1,
        "robot": "unitree_go2",
        "policy_file": policy_file,
        "sample_dt": SAMPLE_DT,
        "observation_dim": LOCOMOTION_POLICY_OBS_DIM,
        "observation_order": LOCOMOTION_POLICY_FEATURES,
        "joint_names": GO2_JOINT_NAMES,
        "dds_motor_indices": GO2_DDS_MOTOR_INDICES,
        "default_joint_pos": GO2_DEFAULT_JOINT_POS.tolist(),
        "action_scale": GO2_ACTION_SCALE.tolist(),
        "p_gains": GO2_P_GAINS.tolist(),
        "d_gains": GO2_D_GAINS.tolist(),
        "action_clip": None,
        "raw_action_safety_limit": MAX_RAW_POLICY_ACTION,
        "target_safety": "joint_position_and_pd_torque_limits",
        "command_limits": {
            "lin_vel_x": [-1.0, 1.0],
            "lin_vel_y": [-1.0, 1.0],
            "ang_vel_z": [-1.0, 1.0],
        },
        "policy_uses_base_linear_velocity": False,
        "isaac_sim_version": "4.5.0",
        "isaac_lab_version": "2.1.0",
        "rsl_rl_version": "2.3.1",
        "python_version": "3.10",
    }


def write_deployment_manifest(path: str | Path, policy_file: str = "policy.pt") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(deployment_manifest(policy_file), indent=2), encoding="utf-8")
    return path.resolve()


def load_deployment_manifest(path: str | Path) -> dict[str, object]:
    path = Path(path).expanduser().resolve()
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("robot") != "unitree_go2":
        raise ValueError(f"{path} is not a Unitree Go2 deployment manifest")
    if tuple(manifest.get("joint_names", ())) != GO2_JOINT_NAMES:
        raise ValueError(f"{path} does not use the canonical Go2 joint order")
    if int(manifest.get("observation_dim", -1)) != LOCOMOTION_POLICY_OBS_DIM:
        raise ValueError(f"{path} has the wrong locomotion observation dimension")
    if tuple(manifest.get("observation_order", ())) != LOCOMOTION_POLICY_FEATURES:
        raise ValueError(f"{path} has the wrong locomotion observation order")
    numeric_contracts = {
        "default_joint_pos": GO2_DEFAULT_JOINT_POS,
        "action_scale": GO2_ACTION_SCALE,
        "p_gains": GO2_P_GAINS,
        "d_gains": GO2_D_GAINS,
    }
    for name, expected in numeric_contracts.items():
        actual = np.asarray(manifest.get(name, ()), dtype=np.float32)
        if actual.shape != expected.shape or not np.allclose(actual, expected):
            raise ValueError(f"{path} has a mismatched {name} contract")
    if not np.isclose(float(manifest.get("sample_dt", -1.0)), SAMPLE_DT):
        raise ValueError(f"{path} does not use the 50 Hz control interval")
    return manifest
