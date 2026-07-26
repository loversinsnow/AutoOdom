from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

from go2_autoodom.constants import (
    AUTOODOM_STAGE1_DIM,
    AUTOODOM_STAGE2_DIM,
    GO2_JOINT_NAMES,
)
from go2_autoodom.data import (
    DataContractError,
    Stage1WindowDataset,
    load_trajectory,
    save_trajectory,
    split_files,
)
from go2_autoodom.model import AutoOdomNet, expand_stage1_to_stage2
from go2_autoodom.tests.helpers import valid_arrays


class DataContractTest(unittest.TestCase):
    def test_round_trip_and_stage1_window_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sim.npz"
            save_trajectory(path, valid_arrays(), source="sim_go2")
            loaded = load_trajectory(path, require_acceleration=True, expected_source_prefix="sim")
            dataset = Stage1WindowDataset([loaded])
            features, target = dataset[0]
            self.assertEqual(features.shape, (50, AUTOODOM_STAGE1_DIM))
            self.assertEqual(target.shape, (3,))
            self.assertEqual(len(dataset), 10)

    def test_booster_or_wrong_joint_order_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wrong.npz"
            payload = valid_arrays()
            np.savez_compressed(
                path,
                **payload,
                joint_names=np.asarray(tuple(reversed(GO2_JOINT_NAMES))),
                sample_dt=np.asarray(0.02, dtype=np.float32),
                source=np.asarray("sim_go2"),
            )
            with self.assertRaisesRegex(DataContractError, "canonical Go2"):
                load_trajectory(path)

    def test_split_is_file_level_and_deterministic(self):
        files = [Path(f"/tmp/trajectory_{index}.npz") for index in range(10)]
        first = split_files(files, seed=42)
        second = split_files(files, seed=42)
        self.assertEqual(first, second)
        flattened = [path for split in first for path in split]
        self.assertEqual(len(flattened), len(set(flattened)))
        self.assertEqual(len(flattened), len(files))


class StageExpansionTest(unittest.TestCase):
    def test_stage2_copies_stage1_and_zero_initializes_acceleration(self):
        torch.manual_seed(7)
        stage1 = AutoOdomNet(AUTOODOM_STAGE1_DIM)
        stage2 = expand_stage1_to_stage2(stage1)
        stage1_state = stage1.state_dict()
        stage2_state = stage2.state_dict()
        first_weight = "encoder.net.0.weight"
        torch.testing.assert_close(
            stage2_state[first_weight][:, :AUTOODOM_STAGE1_DIM, :],
            stage1_state[first_weight],
        )
        self.assertEqual(
            int(torch.count_nonzero(stage2_state[first_weight][:, AUTOODOM_STAGE1_DIM:, :])),
            0,
        )
        for name, value in stage1_state.items():
            if name != first_weight:
                torch.testing.assert_close(stage2_state[name], value)
        self.assertEqual(stage2.input_dim, AUTOODOM_STAGE2_DIM)


if __name__ == "__main__":
    unittest.main()
