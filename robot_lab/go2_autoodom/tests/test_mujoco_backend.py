from __future__ import annotations

import unittest

import numpy as np

from go2_autoodom.constants import GO2_DEFAULT_JOINT_POS, GO2_TORQUE_LIMITS, SAMPLE_DT

try:
    import mujoco  # noqa: F401
except ImportError:
    mujoco = None


@unittest.skipIf(mujoco is None, "MuJoCo is not available in this environment")
class MujocoBackendContractTest(unittest.TestCase):
    def test_local_model_compiles_and_steps_in_canonical_order(self):
        from go2_autoodom.mujoco_backend import MujocoGo2Backend

        backend = MujocoGo2Backend()
        try:
            state = backend.read_state()
            np.testing.assert_allclose(state.joint_pos, GO2_DEFAULT_JOINT_POS)
            self.assertEqual(state.joint_vel.shape, (12,))
            self.assertEqual(state.gyro.shape, (3,))
            self.assertEqual(state.acceleration.shape, (3,))
            np.testing.assert_allclose(
                backend.model.actuator_ctrlrange[backend.actuator_ids],
                np.column_stack([-GO2_TORQUE_LIMITS, GO2_TORQUE_LIMITS]),
            )
            applied = backend.apply_action(np.zeros(12, dtype=np.float32), state)
            self.assertEqual(applied.shape, (12,))
            self.assertAlmostEqual(backend.true_pose().timestamp, SAMPLE_DT, places=6)
        finally:
            backend.close()


if __name__ == "__main__":
    unittest.main()
