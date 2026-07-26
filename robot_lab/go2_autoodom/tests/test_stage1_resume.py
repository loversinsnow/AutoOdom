from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest import mock

import torch

from go2_autoodom.artifacts import STAGE1_LAST_FILENAME
from go2_autoodom.data import save_trajectory
from go2_autoodom.tests.helpers import valid_arrays
from go2_autoodom.train_stage1 import _restore_scheduler, main


class Stage1ResumeTest(unittest.TestCase):
    def test_resume_continues_epoch_and_loss_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_dir = root / "data"
            output_dir = root / "odometry"
            for index in range(3):
                save_trajectory(
                    data_dir / f"trajectory_{index}.npz",
                    valid_arrays(),
                    source="sim_go2",
                )

            common_args = [
                "train_stage1",
                "--data",
                str(data_dir / "*.npz"),
                "--output-dir",
                str(output_dir),
                "--batch-size",
                "32",
                "--workers",
                "0",
                "--seed",
                "7",
                "--device",
                "cpu",
            ]
            with mock.patch("sys.argv", [*common_args, "--epochs", "1"]):
                with contextlib.redirect_stdout(io.StringIO()):
                    main()

            checkpoint_path = output_dir / STAGE1_LAST_FILENAME
            first = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
            self.assertEqual(first["epoch"], 1)
            self.assertEqual(first["scheduler_state_dict"]["last_epoch"], 1)
            self.assertIn("rng_state", first)

            with mock.patch("sys.argv", [*common_args, "--epochs", "2", "--resume"]):
                with contextlib.redirect_stdout(io.StringIO()):
                    main()

            resumed = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
            self.assertEqual(resumed["epoch"], 2)
            self.assertEqual(len(resumed["train_losses"]), 2)
            self.assertEqual(len(resumed["validation_losses"]), 2)
            self.assertEqual(resumed["scheduler_state_dict"]["last_epoch"], 2)
            summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["epochs"], 2)
            self.assertEqual(Path(summary["resumed_from"]), checkpoint_path.resolve())

    def test_legacy_checkpoint_reconstructs_cosine_scheduler(self):
        parameter = torch.nn.Parameter(torch.tensor([1.0]))
        optimizer = torch.optim.Adam([parameter], lr=1.0e-3)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=100,
            eta_min=1.0e-6,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            scheduler.step(28)
        expected_lr = optimizer.param_groups[0]["lr"]
        optimizer_state = optimizer.state_dict()

        resumed_parameter = torch.nn.Parameter(torch.tensor([1.0]))
        resumed_optimizer = torch.optim.Adam([resumed_parameter], lr=1.0e-3)
        resumed_optimizer.load_state_dict(optimizer_state)
        resumed_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            resumed_optimizer,
            T_max=100,
            eta_min=1.0e-6,
        )
        warning = _restore_scheduler(
            resumed_scheduler,
            {},
            completed_epoch=28,
            total_epochs=100,
        )

        self.assertIn("predates scheduler-state", warning)
        self.assertEqual(resumed_scheduler.last_epoch, 28)
        self.assertAlmostEqual(resumed_optimizer.param_groups[0]["lr"], expected_lr)


if __name__ == "__main__":
    unittest.main()
