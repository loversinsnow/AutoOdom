from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

from go2_autoodom.constants import (
    GO2_DDS_MOTOR_INDICES,
    GO2_DEFAULT_JOINT_POS,
    GO2_D_GAINS,
    GO2_JOINT_LIMIT_HIGH,
    GO2_JOINT_LIMIT_LOW,
    GO2_JOINT_NAMES,
    GO2_P_GAINS,
    GO2_TORQUE_LIMITS,
    LOCOMOTION_POLICY_OBS_DIM,
)
from go2_autoodom.deployment import write_deployment_manifest
from go2_autoodom.real.low_level import Go2State
from go2_autoodom.real.low_level import safe_policy_targets
from go2_autoodom.real.mocap import (
    MOCAP_TO_WORLD,
    REFERENCE_MARKER_IN_BODY,
    MocapUnavailable,
    compute_go2_pose,
)
from go2_autoodom.real.remote import RemoteButtons, parse_remote
from go2_autoodom.real.policy import Go2LocomotionPolicy


def _rotation_xyz(roll: float, pitch: float, yaw: float) -> np.ndarray:
    cx, sx = np.cos(roll), np.sin(roll)
    cy, sy = np.cos(pitch), np.sin(pitch)
    cz, sz = np.cos(yaw), np.sin(yaw)
    rotation_x = np.asarray([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    rotation_y = np.asarray([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rotation_z = np.asarray([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rotation_z @ rotation_y @ rotation_x


class JointAndSafetyContractTest(unittest.TestCase):
    def test_canonical_joint_and_dds_order(self):
        self.assertEqual(len(GO2_JOINT_NAMES), 12)
        self.assertEqual(GO2_DDS_MOTOR_INDICES, (3, 0, 9, 6, 4, 1, 10, 7, 5, 2, 11, 8))
        self.assertEqual(len(set(GO2_DDS_MOTOR_INDICES)), 12)

    def test_policy_targets_respect_torque_and_joint_limits(self):
        joint_pos = GO2_DEFAULT_JOINT_POS.copy()
        joint_vel = np.linspace(-2.0, 2.0, 12, dtype=np.float32)
        applied, targets = safe_policy_targets(np.full(12, 10.0), joint_pos, joint_vel)
        torque = GO2_P_GAINS * (targets - joint_pos) - GO2_D_GAINS * joint_vel
        self.assertTrue(np.all(np.abs(torque) <= GO2_TORQUE_LIMITS + 1.0e-4))
        self.assertTrue(np.all(targets >= GO2_JOINT_LIMIT_LOW))
        self.assertTrue(np.all(targets <= GO2_JOINT_LIMIT_HIGH))
        self.assertTrue(np.isfinite(applied).all())


class RemoteContractTest(unittest.TestCase):
    def test_buttons_axes_and_velocity_mapping(self):
        raw = bytearray(24)
        struct.pack_into("<H", raw, 2, int(RemoteButtons.R1 | RemoteButtons.R2))
        struct.pack_into("<f", raw, 4, 0.5)
        struct.pack_into("<f", raw, 8, -0.25)
        struct.pack_into("<f", raw, 12, 0.1)
        struct.pack_into("<f", raw, 20, 0.8)
        remote = parse_remote(raw)
        self.assertTrue(remote.emergency_stop)
        self.assertTrue(remote.buttons & RemoteButtons.R1)
        np.testing.assert_allclose(remote.velocity_command(), [0.8, -0.25, 0.25], atol=1.0e-6)


class PolicyObservationContractTest(unittest.TestCase):
    def test_torchscript_policy_uses_the_45_channel_deployable_observation(self):
        class ZeroPolicy(torch.nn.Module):
            def forward(self, observation):
                return torch.zeros((observation.shape[0], 12), dtype=observation.dtype)

        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            traced = torch.jit.trace(ZeroPolicy(), torch.zeros(1, LOCOMOTION_POLICY_OBS_DIM))
            traced.save(str(directory / "policy.pt"))
            manifest = write_deployment_manifest(directory / "deployment.json")
            policy = Go2LocomotionPolicy(manifest)
            remote = parse_remote(bytes(24))
            state = Go2State(
                joint_pos=GO2_DEFAULT_JOINT_POS.copy(),
                joint_vel=np.zeros(12, dtype=np.float32),
                joint_torque=np.zeros(12, dtype=np.float32),
                gyro=np.zeros(3, dtype=np.float32),
                acceleration=np.zeros(3, dtype=np.float32),
                quaternion_wxyz=np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
                rotation=np.eye(3, dtype=np.float32),
                remote=remote,
                timestamp=0.0,
            )
            observation = policy.observation(state, np.zeros(3, dtype=np.float32))
            self.assertEqual(observation.shape, (LOCOMOTION_POLICY_OBS_DIM,))
            np.testing.assert_allclose(policy.act(state, np.zeros(3, dtype=np.float32)), 0.0)


class MocapContractTest(unittest.TestCase):
    def test_marker_grid_recovers_pose(self):
        origin = np.asarray([1.2, -0.4, 0.31])
        rotation = _rotation_xyz(0.18, -0.12, 0.73)
        local_markers = {
            5: REFERENCE_MARKER_IN_BODY,
            3: np.asarray([0.24, -0.13, 0.12]),
            7: np.asarray([0.00, -0.13, 0.12]),
            8: np.asarray([-0.24, -0.13, 0.12]),
            2: np.asarray([0.24, 0.13, 0.12]),
            1: np.asarray([0.00, 0.13, 0.12]),
            6: np.asarray([-0.24, 0.13, 0.12]),
        }
        raw = {
            index: MOCAP_TO_WORLD.T @ (origin + rotation @ local)
            for index, local in local_markers.items()
        }
        pose = compute_go2_pose(raw)
        np.testing.assert_allclose(pose.position, origin, atol=1.0e-6)
        np.testing.assert_allclose(pose.rotation, rotation, atol=1.0e-6)

    def test_missing_redundancy_is_rejected(self):
        with self.assertRaises(MocapUnavailable):
            compute_go2_pose({5: np.zeros(3), 1: np.ones(3), 2: np.ones(3)})


if __name__ == "__main__":
    unittest.main()
