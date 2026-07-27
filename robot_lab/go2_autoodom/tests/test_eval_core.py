from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from go2_autoodom.constants import GO2_DEFAULT_JOINT_POS, SAMPLE_DT
from go2_autoodom.eval_commands import EvalCommand
from go2_autoodom.eval_core import CommandEvaluator, EvaluationConfig, TruePose
from go2_autoodom.real.low_level import Go2State
from go2_autoodom.real.remote import parse_remote


class FakePolicy:
    def __init__(self):
        self.previous_action = np.zeros(12, dtype=np.float32)

    def reset(self):
        self.previous_action.fill(0.0)

    def act(self, state, command):
        action = np.zeros(12, dtype=np.float32)
        action[:2] = command[:2]
        self.previous_action = action.copy()
        return action


class FakeEstimator:
    stage = 1

    def __init__(self, step_world=(0.0, 0.0, 0.0)):
        self.step_world = np.asarray(step_world, dtype=np.float32)
        self.reset()

    def reset(self):
        self.world_position = np.zeros(3, dtype=np.float32)

    def update(self, **_):
        self.world_position += self.step_world
        return self.step_world.copy(), self.world_position.copy()


class RecordingEstimator(FakeEstimator):
    def __init__(self):
        super().__init__()
        self.joint_commands = []

    def update(self, **inputs):
        self.joint_commands.append(np.asarray(inputs["joint_commands"], dtype=np.float32).copy())
        return super().update(**inputs)


class FakeBackend:
    control_dt = SAMPLE_DT

    def __init__(self, true_step=(0.0, 0.0, 0.0)):
        self.position = np.zeros(3, dtype=np.float32)
        self.true_step = np.asarray(true_step, dtype=np.float32)
        self.time = 0.0

    def read_state(self):
        return Go2State(
            joint_pos=GO2_DEFAULT_JOINT_POS.copy(),
            joint_vel=np.zeros(12, dtype=np.float32),
            joint_torque=np.zeros(12, dtype=np.float32),
            gyro=np.zeros(3, dtype=np.float32),
            acceleration=np.zeros(3, dtype=np.float32),
            quaternion_wxyz=np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
            rotation=np.eye(3, dtype=np.float32),
            remote=parse_remote(bytes(24)),
            timestamp=self.time,
        )

    def true_pose(self):
        return TruePose(self.position.copy(), np.eye(3, dtype=np.float32), self.time)

    def apply_action(self, action, state):
        self.position += self.true_step
        self.time += self.control_dt
        return np.asarray(action, dtype=np.float32).reshape(12)


class LimitingBackend(FakeBackend):
    def apply_action(self, action, state):
        super().apply_action(action, state)
        return np.zeros(12, dtype=np.float32)


class ClosedLoopEvaluationTest(unittest.TestCase):
    def _evaluator(self, directory: Path, backend, estimator):
        return CommandEvaluator(
            backend=backend,
            policy=FakePolicy(),
            estimator=estimator,
            output_dir=directory,
            origin2_relative_pose=np.asarray([0.0, 1.0, 0.0], dtype=np.float32),
            config=EvaluationConfig(zero_command_steps=0),
        )

    def test_estimator_reaching_goal_cannot_fake_success(self):
        with tempfile.TemporaryDirectory() as directory:
            evaluator = self._evaluator(
                Path(directory),
                FakeBackend(true_step=(0.0, 0.0, 0.0)),
                FakeEstimator(step_world=(0.5, 0.0, 0.0)),
            )
            result = evaluator._run_command(
                EvalCommand(1, np.asarray([0.5, 0.0], dtype=np.float32)),
                1,
                "origin_1",
            )
            self.assertFalse(result["success"])
            self.assertTrue(result["timed_out"])

    def test_true_position_reaching_goal_succeeds_despite_bad_estimate(self):
        with tempfile.TemporaryDirectory() as directory:
            evaluator = self._evaluator(
                Path(directory),
                FakeBackend(true_step=(0.25, 0.0, 0.0)),
                FakeEstimator(step_world=(-10.0, 0.0, 0.0)),
            )
            result = evaluator._run_command(
                EvalCommand(1, np.asarray([0.5, 0.0], dtype=np.float32)),
                1,
                "origin_1",
            )
            self.assertTrue(result["success"])
            self.assertEqual(result["steps"], 1)

    def test_estimator_receives_raw_policy_action_not_limited_backend_target(self):
        with tempfile.TemporaryDirectory() as directory:
            estimator = RecordingEstimator()
            evaluator = self._evaluator(Path(directory), LimitingBackend(), estimator)
            evaluator._run_command(
                EvalCommand(1, np.asarray([0.5, 0.0], dtype=np.float32)),
                1,
                "origin_1",
            )
            np.testing.assert_allclose(estimator.joint_commands[0], 0.0)
            self.assertGreater(float(estimator.joint_commands[1][0]), 0.0)


if __name__ == "__main__":
    unittest.main()
