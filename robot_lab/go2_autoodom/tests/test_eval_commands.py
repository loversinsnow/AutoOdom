from __future__ import annotations

import math
import unittest

import numpy as np

from go2_autoodom.eval_commands import (
    EVAL_COMMAND_PATH,
    EVAL_COMMAND_SHA256,
    command_uses_origin2,
    compose_pose2d,
    load_eval_commands,
    load_origin2_relative_pose,
    sha256_file,
)
from go2_autoodom.eval_core import (
    TruePose,
    command_succeeded,
    command_timeout,
    horizontal_basis,
    navigation_velocity_command,
    true_goal_position,
)


class EvaluationCommandContractTest(unittest.TestCase):
    def test_builtin_command_set_is_the_fixed_100_line_asset(self):
        commands = load_eval_commands()
        self.assertEqual(len(commands), 100)
        self.assertEqual(sha256_file(EVAL_COMMAND_PATH), EVAL_COMMAND_SHA256)
        np.testing.assert_allclose(commands[0].position, [0.7906490326, -0.9997712374])
        np.testing.assert_allclose(commands[-1].position, [1.1994806528, 0.6659362912])
        self.assertTrue(command_uses_origin2(commands[0]))
        self.assertFalse(command_uses_origin2(commands[-1]))

    def test_timeout_matches_distance_over_speed_with_reference_scale(self):
        self.assertAlmostEqual(command_timeout([0.6, 0.8]), 1.0 / 0.8 * 1.01)

    def test_origin2_is_composed_in_fresh_origin1_frame(self):
        relative = load_origin2_relative_pose()
        np.testing.assert_allclose(
            relative,
            [-0.2578957243, 1.9741621243, 0.0459571226],
            atol=1.0e-7,
        )
        base = np.asarray([1.0, 2.0, math.pi / 2.0], dtype=np.float32)
        composed = compose_pose2d(base, relative)
        np.testing.assert_allclose(
            composed[:2],
            [1.0 - relative[1], 2.0 + relative[0]],
            atol=1.0e-6,
        )
        self.assertAlmostEqual(composed[2], math.pi / 2.0 + float(relative[2]), places=6)


class EvaluationGeometryContractTest(unittest.TestCase):
    def test_episode_frame_uses_forward_and_left_axes(self):
        yaw = math.pi / 2.0
        rotation = np.asarray(
            [[math.cos(yaw), -math.sin(yaw), 0.0], [math.sin(yaw), math.cos(yaw), 0.0], [0, 0, 1]],
            dtype=np.float32,
        )
        pose = TruePose(np.asarray([1.0, 2.0, 0.3], dtype=np.float32), rotation, 0.0)
        np.testing.assert_allclose(horizontal_basis(rotation), [[0.0, -1.0], [1.0, 0.0]], atol=1.0e-6)
        np.testing.assert_allclose(true_goal_position(pose, [2.0, 1.0])[:2], [0.0, 4.0], atol=1.0e-6)

    def test_navigation_uses_estimator_error_and_zero_yaw(self):
        command = navigation_velocity_command(
            estimated_position_world=np.asarray([0.5, 0.0, 0.0]),
            estimated_goal_world=np.asarray([2.0, 0.0, 0.0]),
            current_world_from_body=np.eye(3),
        )
        np.testing.assert_allclose(command, [0.8, 0.0, 0.0], atol=1.0e-6)

    def test_success_depends_only_on_true_xy_distance(self):
        self.assertTrue(command_succeeded([1.0, 2.0, 100.0], [1.29, 2.0, -100.0]))
        self.assertFalse(command_succeeded([1.0, 2.0, 0.0], [1.301, 2.0, 0.0]))


if __name__ == "__main__":
    unittest.main()
