"""Repository-local copy and parser for the fixed 100-command evaluation set."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .constants import PACKAGE_DIR


EVAL_COMMAND_PATH = PACKAGE_DIR / "assets" / "eval_command.txt"
EVAL_COMMAND_SHA256 = "ac4de585a4a75950e22f7302eb4c5aee7f07675f107339cad1d6b1f5c7e17605"
ORIGIN_CALIBRATION_PATH = PACKAGE_DIR / "assets" / "origins_position_orient.json"


@dataclass(frozen=True)
class EvalCommand:
    source_index: int
    position: np.ndarray


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_eval_commands(
    path: str | Path = EVAL_COMMAND_PATH,
    *,
    start: int = 1,
    count: int = 100,
    verify_builtin: bool = True,
) -> list[EvalCommand]:
    """Load the first two columns as forward/left displacement commands."""
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Evaluation command file not found: {path}")
    if start < 1:
        raise ValueError(f"Command start must be at least 1, got {start}")
    if count < 1:
        raise ValueError(f"Command count must be positive, got {count}")
    if verify_builtin and path == EVAL_COMMAND_PATH.resolve():
        actual_sha = sha256_file(path)
        if actual_sha != EVAL_COMMAND_SHA256:
            raise ValueError(
                f"Built-in evaluation commands have checksum {actual_sha}, expected {EVAL_COMMAND_SHA256}"
            )

    commands: list[EvalCommand] = []
    command_index = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            raise ValueError(f"{path}:{line_number} must contain at least pos_x and pos_y")
        try:
            position = np.asarray([float(parts[0]), float(parts[1])], dtype=np.float32)
        except ValueError as exc:
            raise ValueError(f"{path}:{line_number} has invalid pos_x/pos_y values") from exc
        if not np.isfinite(position).all():
            raise ValueError(f"{path}:{line_number} contains NaN or infinity")
        command_index += 1
        if command_index < start:
            continue
        commands.append(EvalCommand(source_index=line_number, position=position))
        if len(commands) == count:
            break
    if len(commands) != count:
        raise ValueError(
            f"Requested {count} commands starting at {start}, but only loaded {len(commands)} from {path}"
        )
    return commands


def load_origin2_relative_pose(path: str | Path = ORIGIN_CALIBRATION_PATH) -> np.ndarray:
    path = Path(path).expanduser().resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        relative = payload["origins"]["origin_2"]["relative_pose"]
        position = np.asarray(relative["position_m"], dtype=np.float64).reshape(2)
        yaw = float(relative["yaw_rad"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid origin calibration JSON: {path}") from exc
    pose = np.asarray([position[0], position[1], yaw], dtype=np.float32)
    if not np.isfinite(pose).all():
        raise ValueError(f"Origin calibration contains NaN or infinity: {path}")
    return pose


def wrap_to_pi(angle: float) -> float:
    return float((angle + math.pi) % (2.0 * math.pi) - math.pi)


def compose_pose2d(base_pose: np.ndarray, relative_pose: np.ndarray) -> np.ndarray:
    """Compose an origin-2 calibration in the freshly measured origin-1 frame."""
    base = np.asarray(base_pose, dtype=np.float64).reshape(3)
    relative = np.asarray(relative_pose, dtype=np.float64).reshape(3)
    if not np.isfinite(np.concatenate([base, relative])).all():
        raise ValueError("Origin poses must contain only finite values")
    cosine = math.cos(float(base[2]))
    sine = math.sin(float(base[2]))
    return np.asarray(
        [
            base[0] + cosine * relative[0] - sine * relative[1],
            base[1] + sine * relative[0] + cosine * relative[1],
            wrap_to_pi(float(base[2] + relative[2])),
        ],
        dtype=np.float32,
    )


def command_uses_origin2(command: EvalCommand) -> bool:
    return float(command.position[1]) < 0.0

