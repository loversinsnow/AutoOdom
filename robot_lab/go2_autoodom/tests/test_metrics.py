from __future__ import annotations

import unittest

import numpy as np

from go2_autoodom.metrics import trajectory_metrics, umeyama_align


class MetricsTest(unittest.TestCase):
    def test_perfect_trajectory_has_zero_error(self):
        increments = np.asarray([[0, 0, 0], [0.1, 0, 0], [0.1, 0.02, 0]], dtype=np.float64)
        rotations = np.repeat(np.eye(3)[None, ...], 3, axis=0)
        positions = np.asarray([[2, 3, 0], [2.1, 3, 0], [2.2, 3.02, 0]], dtype=np.float64)
        metrics = trajectory_metrics(increments, increments, rotations, positions)
        for name in ("step_rmse", "rpe_translation", "ate_origin", "ate_umeyama", "final_drift"):
            self.assertAlmostEqual(metrics[name], 0.0, places=8)

    def test_umeyama_removes_rigid_transform_without_scale(self):
        source = np.asarray([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=np.float64)
        rotation = np.asarray([[0, -1, 0], [1, 0, 0], [0, 0, 1]], dtype=np.float64)
        target = (rotation @ source.T).T + np.asarray([3, -2, 0.5])
        np.testing.assert_allclose(umeyama_align(source, target), target, atol=1.0e-8)


if __name__ == "__main__":
    unittest.main()
