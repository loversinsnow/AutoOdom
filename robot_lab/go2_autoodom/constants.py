"""Shared Go2 ordering, control, and data-contract constants."""

from __future__ import annotations

from pathlib import Path

import numpy as np


GO2_JOINT_NAMES = (
    "FL_hip_joint",
    "FR_hip_joint",
    "RL_hip_joint",
    "RR_hip_joint",
    "FL_thigh_joint",
    "FR_thigh_joint",
    "RL_thigh_joint",
    "RR_thigh_joint",
    "FL_calf_joint",
    "FR_calf_joint",
    "RL_calf_joint",
    "RR_calf_joint",
)

# Canonical AutoOdom order -> Unitree DDS motor_state/motor_cmd order.
GO2_DDS_MOTOR_INDICES = (3, 0, 9, 6, 4, 1, 10, 7, 5, 2, 11, 8)
GO2_DDS_SIGNS = (1.0,) * 12

GO2_DEFAULT_JOINT_POS = np.asarray(
    [0.1, -0.1, 0.1, -0.1, 0.8, 0.8, 1.0, 1.0, -1.5, -1.5, -1.5, -1.5],
    dtype=np.float32,
)
GO2_ACTION_SCALE = np.asarray([0.125] * 4 + [0.25] * 8, dtype=np.float32)
GO2_P_GAINS = np.full(12, 25.0, dtype=np.float32)
GO2_D_GAINS = np.full(12, 0.5, dtype=np.float32)

GO2_JOINT_LIMIT_LOW = np.asarray(
    [-1.0472] * 4 + [-1.5708, -1.5708, -0.5236, -0.5236] + [-2.7227] * 4,
    dtype=np.float32,
)
GO2_JOINT_LIMIT_HIGH = np.asarray(
    [1.0472] * 4 + [3.4907, 3.4907, 4.5379, 4.5379] + [-0.83776] * 4,
    dtype=np.float32,
)
GO2_TORQUE_LIMITS = np.asarray([23.7] * 8 + [45.43] * 4, dtype=np.float32)

SAMPLE_DT = 0.02
HISTORY_LENGTH = 50
AUTOODOM_STAGE1_DIM = 12 + 12 + 3 + 3 + 12 + 3
AUTOODOM_STAGE2_DIM = AUTOODOM_STAGE1_DIM + 3
LOCOMOTION_POLICY_OBS_DIM = 3 + 3 + 3 + 12 + 12 + 12
DATA_FORMAT_VERSION = "go2-autoodom-v1"
TASK_ID = "AutoOdom-Isaac-Velocity-Flat-Unitree-Go2-v0"
PLAY_TASK_ID = "AutoOdom-Isaac-Velocity-Flat-Unitree-Go2-Play-v0"

AUTOODOM_STAGE1_FEATURES = (
    "joint_pos[12]",
    "joint_vel[12]",
    "gyro_ang_vel[3]",
    "gravity_vec[3]",
    "joint_commands[12]",
    "previous_predicted_increment[3]",
)
AUTOODOM_STAGE2_FEATURES = AUTOODOM_STAGE1_FEATURES + ("imu_lin_acc[3]",)
LOCOMOTION_POLICY_FEATURES = (
    "base_ang_vel[3]",
    "projected_gravity[3]",
    "velocity_command[3]",
    "joint_pos_relative[12]",
    "joint_vel[12]",
    "previous_action[12]",
)

PACKAGE_DIR = Path(__file__).resolve().parent
ROBOT_LAB_DIR = PACKAGE_DIR.parent
REPOSITORY_DIR = ROBOT_LAB_DIR.parent
DEFAULT_UNITREE_SDK_DIR = REPOSITORY_DIR.parent / "unitree_sdk2_python"
