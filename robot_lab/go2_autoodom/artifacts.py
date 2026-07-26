"""Run-directory and artifact conventions shared by simulation and real training."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import torch

from .deployment import load_deployment_manifest


SIMULATION_LOG_ROOT = Path("logs/autoodom_sim")
REAL_LOG_ROOT = Path("logs/autoodom_real")
SIMULATION_EVAL_LOG_ROOT = Path("logs/autoodom_sim_eval")
REAL_EVAL_LOG_ROOT = Path("logs/autoodom_real_eval")
EXPORTED_DIRNAME = "exported"
ODOMETRY_DIRNAME = "odometry"
POLICY_FILENAME = "policy.pt"
DEPLOYMENT_FILENAME = "deployment.json"
RUN_MANIFEST_FILENAME = "run_manifest.json"
STAGE1_BEST_FILENAME = "auto_odom_stage1_sim_best.pth"
STAGE1_LAST_FILENAME = "auto_odom_stage1_sim_last.pth"
STAGE2_BEST_FILENAME = "auto_odom_stage2_real_best.pth"
STAGE2_LAST_FILENAME = "auto_odom_stage2_real_last.pth"

_MODEL_CHECKPOINT_PATTERN = re.compile(r"model_(\d+)\.pt$")


@dataclass(frozen=True)
class EvaluationBundle:
    """Resolved control-policy and odometry artifacts from one timestamp run."""

    run_dir: Path
    deployment_json: Path
    policy_path: Path
    odometry_checkpoint: Path
    stage: int
    training_domain: str


def create_timestamped_run(log_root: str | Path, *, timestamp: str | None = None) -> Path:
    """Create ``<log_root>/<timestamp>`` without reusing an existing run."""
    root = Path(log_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    base_name = timestamp or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    candidate = root / base_name
    suffix = 1
    while candidate.exists():
        candidate = root / f"{base_name}_{suffix:02d}"
        suffix += 1
    candidate.mkdir(parents=False, exist_ok=False)
    return candidate


def ensure_run_dir(path: str | Path) -> Path:
    run_dir = Path(path).expanduser().resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def exported_dir(run_dir: str | Path) -> Path:
    path = ensure_run_dir(run_dir) / EXPORTED_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def odometry_dir(run_dir: str | Path) -> Path:
    path = ensure_run_dir(run_dir) / ODOMETRY_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_dir(run_dir: str | Path, domain: str) -> Path:
    if domain not in {"sim", "real"}:
        raise ValueError(f"Unsupported data domain: {domain!r}")
    path = ensure_run_dir(run_dir) / "data" / domain
    path.mkdir(parents=True, exist_ok=True)
    return path


def latest_model_checkpoint(run_dir: str | Path) -> Path:
    """Resolve the numerically latest RSL-RL ``model_<iteration>.pt`` file."""
    candidates: list[tuple[int, Path]] = []
    for path in ensure_run_dir(run_dir).glob("model_*.pt"):
        match = _MODEL_CHECKPOINT_PATTERN.fullmatch(path.name)
        if match:
            candidates.append((int(match.group(1)), path))
    if not candidates:
        raise FileNotFoundError(f"No model_<iteration>.pt checkpoint found in {Path(run_dir)}")
    return max(candidates, key=lambda item: item[0])[1].resolve()


def _resolve_requested_run(log_root: Path, load_run: str | Path) -> Path:
    requested = Path(load_run).expanduser()
    if requested.is_dir():
        return requested.resolve()
    candidate = log_root / requested
    if candidate.is_dir():
        return candidate.resolve()
    raise FileNotFoundError(
        f"Run {load_run!s} was not found as a directory or under {log_root}"
    )


def _evaluation_bundle_from_run(
    run_dir: Path,
    *,
    stage: int,
    training_domain: str,
    odometry_filename: str,
    deployment_override: str | Path | None = None,
    odometry_override: str | Path | None = None,
) -> EvaluationBundle:
    deployment_json = (
        Path(deployment_override).expanduser().resolve()
        if deployment_override is not None
        else run_dir / EXPORTED_DIRNAME / DEPLOYMENT_FILENAME
    )
    odometry_checkpoint = (
        Path(odometry_override).expanduser().resolve()
        if odometry_override is not None
        else run_dir / ODOMETRY_DIRNAME / odometry_filename
    )
    if not deployment_json.is_file():
        raise FileNotFoundError(f"Deployment manifest is missing: {deployment_json}")
    manifest = load_deployment_manifest(deployment_json)
    policy_path = (deployment_json.parent / str(manifest["policy_file"])).resolve()
    if policy_path.parent != deployment_json.parent or not policy_path.is_file():
        raise FileNotFoundError(
            f"Deployment policy must be stored beside its manifest: {policy_path}"
        )
    if not odometry_checkpoint.is_file():
        raise FileNotFoundError(f"Odometry checkpoint is missing: {odometry_checkpoint}")

    run_manifest_path = run_dir / RUN_MANIFEST_FILENAME
    if run_manifest_path.is_file():
        run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
        if int(run_manifest.get("stage", -1)) != stage:
            raise ValueError(
                f"{run_manifest_path} is Stage {run_manifest.get('stage')}, expected Stage {stage}"
            )
        if run_manifest.get("training_domain") != training_domain:
            raise ValueError(
                f"{run_manifest_path} has training_domain={run_manifest.get('training_domain')!r}, "
                f"expected {training_domain!r}"
            )
    return EvaluationBundle(
        run_dir=run_dir.resolve(),
        deployment_json=deployment_json,
        policy_path=policy_path,
        odometry_checkpoint=odometry_checkpoint,
        stage=stage,
        training_domain=training_domain,
    )


def resolve_evaluation_bundle(
    log_root: str | Path,
    *,
    stage: int,
    load_run: str | Path | None = None,
    deployment_override: str | Path | None = None,
    odometry_override: str | Path | None = None,
) -> EvaluationBundle:
    """Resolve one complete timestamp run, choosing the latest complete run by default."""
    if stage not in {1, 2}:
        raise ValueError(f"Evaluation stage must be 1 or 2, got {stage}")
    training_domain = "simulation" if stage == 1 else "real"
    odometry_filename = STAGE1_BEST_FILENAME if stage == 1 else STAGE2_BEST_FILENAME
    root = Path(log_root).expanduser().resolve()

    if load_run is not None:
        run_dir = _resolve_requested_run(root, load_run)
        return _evaluation_bundle_from_run(
            run_dir,
            stage=stage,
            training_domain=training_domain,
            odometry_filename=odometry_filename,
            deployment_override=deployment_override,
            odometry_override=odometry_override,
        )

    if not root.is_dir():
        raise FileNotFoundError(f"Run root does not exist: {root}")
    failures: list[str] = []
    for run_dir in sorted(
        (path.resolve() for path in root.iterdir() if path.is_dir()),
        key=lambda path: path.name,
        reverse=True,
    ):
        try:
            return _evaluation_bundle_from_run(
                run_dir,
                stage=stage,
                training_domain=training_domain,
                odometry_filename=odometry_filename,
                deployment_override=deployment_override,
                odometry_override=odometry_override,
            )
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            failures.append(f"{run_dir.name}: {exc}")
    detail = "\n  ".join(failures[:5])
    suffix = f"\n  {detail}" if detail else ""
    raise FileNotFoundError(
        f"No complete Stage {stage} {training_domain} run was found under {root}.{suffix}"
    )


def atomic_json_dump(payload: Any, path: str | Path) -> Path:
    """Write JSON atomically so interrupted hardware evaluation keeps valid progress."""
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _copy_without_overwrite(source: Path, destination: Path) -> None:
    if destination.exists():
        if _sha256(source) != _sha256(destination):
            raise FileExistsError(f"Refusing to overwrite a different artifact: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_deployment_bundle(deployment_json: str | Path, run_dir: str | Path) -> Path:
    """Copy a validated deployment bundle to ``<run>/exported`` with canonical names."""
    source_manifest = Path(deployment_json).expanduser().resolve()
    manifest = load_deployment_manifest(source_manifest)
    source_policy = (source_manifest.parent / str(manifest["policy_file"])).resolve()
    if source_policy.parent != source_manifest.parent or not source_policy.is_file():
        raise FileNotFoundError(f"Deployment policy must be beside its manifest: {source_policy}")

    destination_dir = exported_dir(run_dir)
    destination_policy = destination_dir / POLICY_FILENAME
    destination_manifest = destination_dir / DEPLOYMENT_FILENAME
    _copy_without_overwrite(source_policy, destination_policy)

    normalized_manifest = dict(manifest)
    normalized_manifest["policy_file"] = POLICY_FILENAME
    serialized = json.dumps(normalized_manifest, indent=2)
    if destination_manifest.exists():
        existing = json.loads(destination_manifest.read_text(encoding="utf-8"))
        if existing != normalized_manifest:
            raise FileExistsError(
                f"Refusing to overwrite a different deployment manifest: {destination_manifest}"
            )
    else:
        destination_manifest.write_text(serialized, encoding="utf-8")
    return destination_manifest.resolve()


def update_run_manifest(
    run_dir: str | Path,
    *,
    stage: int,
    training_domain: str,
    extra: dict[str, Any] | None = None,
) -> Path:
    if (stage, training_domain) not in {(1, "simulation"), (2, "real")}:
        raise ValueError(f"Invalid Stage/domain pair: Stage {stage}, {training_domain!r}")
    run_dir = ensure_run_dir(run_dir)
    path = run_dir / RUN_MANIFEST_FILENAME
    payload: dict[str, Any] = {}
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        existing_stage = payload.get("stage")
        existing_domain = payload.get("training_domain")
        if existing_stage not in {None, stage} or existing_domain not in {None, training_domain}:
            raise ValueError(f"{path} belongs to a different Stage/domain")
    payload.update(
        {
            "format_version": 1,
            "stage": stage,
            "training_domain": training_domain,
            "control_policy": f"{EXPORTED_DIRNAME}/{POLICY_FILENAME}",
            "deployment_manifest": f"{EXPORTED_DIRNAME}/{DEPLOYMENT_FILENAME}",
            "odometry_directory": ODOMETRY_DIRNAME,
        }
    )
    if extra:
        payload.update(extra)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path.resolve()


def atomic_torch_save(payload: Any, path: str | Path) -> Path:
    """Save a checkpoint atomically so an interrupted run cannot leave a partial file."""
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        torch.save(payload, temporary_path)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return path
