from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import torch

from go2_autoodom.artifacts import (
    DEPLOYMENT_FILENAME,
    POLICY_FILENAME,
    STAGE1_BEST_FILENAME,
    atomic_torch_save,
    copy_deployment_bundle,
    create_timestamped_run,
    latest_model_checkpoint,
    resolve_evaluation_bundle,
    update_run_manifest,
)
from go2_autoodom.deployment import write_deployment_manifest


class ArtifactLayoutTest(unittest.TestCase):
    def test_timestamp_runs_are_unique(self):
        with tempfile.TemporaryDirectory() as directory:
            first = create_timestamped_run(directory, timestamp="2026-07-24_12-00-00")
            second = create_timestamped_run(directory, timestamp="2026-07-24_12-00-00")
            self.assertEqual(first.name, "2026-07-24_12-00-00")
            self.assertEqual(second.name, "2026-07-24_12-00-00_01")

    def test_latest_rsl_rl_checkpoint_uses_numeric_iteration(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            for name in ("model_9.pt", "model_100.pt", "model_latest.pt"):
                (run_dir / name).write_bytes(b"checkpoint")
            self.assertEqual(latest_model_checkpoint(run_dir).name, "model_100.pt")

    def test_control_bundle_and_odometry_have_separate_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / "controller.pt").write_bytes(b"go2-control-policy")
            write_deployment_manifest(source / DEPLOYMENT_FILENAME, "controller.pt")

            run_dir = root / "logs" / "autoodom_real" / "2026-07-24_12-00-00"
            copied_manifest = copy_deployment_bundle(source / DEPLOYMENT_FILENAME, run_dir)
            self.assertEqual(copied_manifest, (run_dir / "exported" / DEPLOYMENT_FILENAME).resolve())
            self.assertEqual((run_dir / "exported" / POLICY_FILENAME).read_bytes(), b"go2-control-policy")
            manifest = json.loads(copied_manifest.read_text(encoding="utf-8"))
            self.assertEqual(manifest["policy_file"], POLICY_FILENAME)

            run_manifest = update_run_manifest(
                run_dir,
                stage=2,
                training_domain="real",
                extra={"control_policy_origin": "copied_for_real_data_collection"},
            )
            metadata = json.loads(run_manifest.read_text(encoding="utf-8"))
            self.assertEqual(metadata["control_policy"], "exported/policy.pt")
            self.assertEqual(metadata["odometry_directory"], "odometry")
            self.assertEqual(metadata["training_domain"], "real")
            with self.assertRaisesRegex(ValueError, "different Stage/domain"):
                update_run_manifest(run_dir, stage=1, training_domain="simulation")

    def test_checkpoint_save_is_atomic_and_loadable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "odometry" / "auto_odom_stage1_sim_best.pth"
            atomic_torch_save({"stage": 1, "value": torch.tensor([2.0])}, path)
            payload = torch.load(path, map_location="cpu", weights_only=False)
            self.assertEqual(payload["stage"], 1)
            torch.testing.assert_close(payload["value"], torch.tensor([2.0]))
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.tmp")), [])

    def test_evaluation_bundle_selects_latest_complete_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for timestamp, complete in (
                ("2026-07-24_10-00-00", True),
                ("2026-07-24_11-00-00", False),
                ("2026-07-24_12-00-00", True),
            ):
                run_dir = root / timestamp
                exported = run_dir / "exported"
                exported.mkdir(parents=True)
                (exported / "policy.pt").write_bytes(timestamp.encode())
                write_deployment_manifest(exported / "deployment.json")
                update_run_manifest(run_dir, stage=1, training_domain="simulation")
                if complete:
                    odometry = run_dir / "odometry"
                    odometry.mkdir()
                    (odometry / STAGE1_BEST_FILENAME).write_bytes(b"checkpoint")

            latest = resolve_evaluation_bundle(root, stage=1)
            self.assertEqual(latest.run_dir.name, "2026-07-24_12-00-00")
            selected = resolve_evaluation_bundle(
                root,
                stage=1,
                load_run="2026-07-24_10-00-00",
            )
            self.assertEqual(selected.run_dir.name, "2026-07-24_10-00-00")

    def test_evaluation_bundle_rejects_wrong_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = root / "2026-07-24_12-00-00"
            exported = run_dir / "exported"
            exported.mkdir(parents=True)
            (exported / "policy.pt").write_bytes(b"policy")
            write_deployment_manifest(exported / "deployment.json")
            odometry = run_dir / "odometry"
            odometry.mkdir()
            (odometry / STAGE1_BEST_FILENAME).write_bytes(b"checkpoint")
            update_run_manifest(run_dir, stage=2, training_domain="real")
            with self.assertRaisesRegex(ValueError, "expected Stage 1"):
                resolve_evaluation_bundle(root, stage=1, load_run=run_dir)


if __name__ == "__main__":
    unittest.main()
