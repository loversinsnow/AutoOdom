"""Eight-marker Go2 pose reconstruction using ROS 2 CLI subprocess readers."""

from __future__ import annotations

import re
import shlex
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np


REFERENCE_MARKER = 5
REFERENCE_MARKER_IN_BODY = np.asarray([0.221, 0.0, 0.1039], dtype=np.float64)
ORIENTATION_GRID = ((3, 7, 8), (2, 1, 6))
MARKER_TOPICS = tuple(f"/Tracker0_Marker{index}/pose" for index in range(1, 9))
TWIST_TOPIC = "/Tracker0/twist"
MOCAP_TO_WORLD = np.asarray([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
DEFAULT_TIMEOUT = 0.5

_FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_POSITION = re.compile(
    rf"position:\s*x:\s*({_FLOAT})\s*y:\s*({_FLOAT})\s*z:\s*({_FLOAT})",
    re.DOTALL,
)
_TWIST = re.compile(
    rf"linear:\s*x:\s*({_FLOAT})\s*y:\s*({_FLOAT})\s*z:\s*({_FLOAT}).*?"
    rf"angular:\s*x:\s*({_FLOAT})\s*y:\s*({_FLOAT})\s*z:\s*({_FLOAT})",
    re.DOTALL,
)


class MocapUnavailable(RuntimeError):
    """Raised when fresh markers cannot define a redundant Go2 frame."""


@dataclass(frozen=True)
class MocapPose:
    position: np.ndarray
    rotation: np.ndarray
    timestamp: float
    linear_velocity_world: np.ndarray | None = None
    angular_velocity_world: np.ndarray | None = None


def parse_pose_chunk(chunk: str) -> np.ndarray | None:
    match = _POSITION.search(chunk)
    if match is None:
        return None
    return np.asarray([float(match.group(index)) for index in range(1, 4)], dtype=np.float64)


def parse_twist_chunk(chunk: str) -> tuple[np.ndarray, np.ndarray] | None:
    match = _TWIST.search(chunk)
    if match is None:
        return None
    linear = np.asarray([float(match.group(index)) for index in range(1, 4)], dtype=np.float64)
    angular = np.asarray([float(match.group(index)) for index in range(4, 7)], dtype=np.float64)
    return linear, angular


def mocap_to_world(vector: np.ndarray) -> np.ndarray:
    return MOCAP_TO_WORLD @ np.asarray(vector, dtype=np.float64)


def _unit_vector(positions: dict[int, np.ndarray], start: int, end: int) -> np.ndarray | None:
    if start not in positions or end not in positions:
        return None
    vector = positions[end] - positions[start]
    norm = float(np.linalg.norm(vector))
    if norm <= 1.0e-4:
        return None
    return vector / norm


def compute_go2_pose(raw_marker_positions: dict[int, np.ndarray], timestamp: float | None = None) -> MocapPose:
    """Recover world position/orientation from the confirmed Go2 marker grid."""
    positions = {index: mocap_to_world(value) for index, value in raw_marker_positions.items()}
    if REFERENCE_MARKER not in positions:
        raise MocapUnavailable("Marker5 translation reference is unavailable")
    orientation_indices = {index for row in ORIENTATION_GRID for index in row}
    fresh = orientation_indices.intersection(positions)
    if len(fresh) < 4:
        raise MocapUnavailable(f"Need at least 4/6 orientation markers, got {len(fresh)}/6")

    x_vectors: list[np.ndarray] = []
    for row in ORIENTATION_GRID:
        # Rows are ordered front -> middle -> rear; rear-to-front is body +X.
        for front_column in range(len(row)):
            for rear_column in range(front_column + 1, len(row)):
                vector = _unit_vector(positions, row[rear_column], row[front_column])
                if vector is not None:
                    x_vectors.append(vector)
    y_vectors = []
    right_row, left_row = ORIENTATION_GRID
    for right_marker, left_marker in zip(right_row, left_row):
        vector = _unit_vector(positions, right_marker, left_marker)
        if vector is not None:
            y_vectors.append(vector)
    if not x_vectors or not y_vectors:
        raise MocapUnavailable("Fresh marker geometry cannot observe both body X and Y axes")

    x_axis = np.mean(x_vectors, axis=0)
    x_axis /= np.linalg.norm(x_axis)
    y_hint = np.mean(y_vectors, axis=0)
    y_hint /= np.linalg.norm(y_hint)
    z_axis = np.cross(x_axis, y_hint)
    z_norm = float(np.linalg.norm(z_axis))
    if z_norm <= 1.0e-4:
        raise MocapUnavailable("Marker axes are nearly collinear")
    z_axis /= z_norm
    y_axis = np.cross(z_axis, x_axis)
    y_axis /= np.linalg.norm(y_axis)
    x_axis = np.cross(y_axis, z_axis)
    x_axis /= np.linalg.norm(x_axis)
    rotation = np.column_stack([x_axis, y_axis, z_axis])
    origin = positions[REFERENCE_MARKER] - rotation @ REFERENCE_MARKER_IN_BODY
    return MocapPose(
        position=origin.astype(np.float32),
        rotation=rotation.astype(np.float32),
        timestamp=time.monotonic() if timestamp is None else float(timestamp),
    )


def _ros_command(arguments: list[str], setup_files: tuple[Path, ...]) -> list[str]:
    existing = [path for path in setup_files if path.is_file()]
    if not existing:
        return ["ros2", *arguments]
    sources = [f"source {shlex.quote(str(path))} >/dev/null 2>&1" for path in existing]
    command = " && ".join(sources + ["exec " + " ".join(shlex.quote(item) for item in ["ros2", *arguments])])
    return ["zsh", "-lc", command]


class _TopicReader:
    def __init__(
        self,
        topic: str,
        parser: Callable[[str], object | None],
        setup_files: tuple[Path, ...],
        message_type: str | None = None,
    ):
        self.topic = topic
        self.parser = parser
        self.setup_files = setup_files
        self.message_type = message_type
        self._value = None
        self._timestamp = 0.0
        self._lock = threading.Lock()
        self._process: subprocess.Popen | None = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        arguments = ["topic", "echo", "--no-arr", self.topic]
        if self.message_type:
            arguments.append(self.message_type)
        try:
            self._process = subprocess.Popen(
                _ros_command(arguments, self.setup_files),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            return
        assert self._process.stdout is not None
        buffer: list[str] = []
        for line in self._process.stdout:
            buffer.append(line)
            if line.strip() == "---":
                value = self.parser("".join(buffer))
                buffer.clear()
                if value is not None:
                    with self._lock:
                        self._value = value
                        self._timestamp = time.monotonic()

    def get(self) -> tuple[object | None, float]:
        with self._lock:
            value = self._value
            age = time.monotonic() - self._timestamp if self._timestamp else float("inf")
            if isinstance(value, np.ndarray):
                value = value.copy()
            elif isinstance(value, tuple):
                value = tuple(item.copy() if isinstance(item, np.ndarray) else item for item in value)
            return value, age

    def close(self) -> None:
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()


class MocapTracker:
    def __init__(
        self,
        *,
        ros_setups: tuple[str | Path, ...] = ("/opt/ros/rolling/setup.zsh",),
        timeout: float = DEFAULT_TIMEOUT,
    ):
        setup_files = tuple(Path(path).expanduser() for path in ros_setups)
        self.timeout = float(timeout)
        self.marker_readers = {
            index: _TopicReader(
                f"/Tracker0_Marker{index}/pose",
                parse_pose_chunk,
                setup_files,
                "geometry_msgs/msg/PoseStamped",
            )
            for index in range(1, 9)
        }
        self.twist_reader = _TopicReader(TWIST_TOPIC, parse_twist_chunk, setup_files)

    def sample(self) -> MocapPose:
        positions = {}
        timestamps = []
        for index, reader in self.marker_readers.items():
            value, age = reader.get()
            if value is not None and age < self.timeout:
                positions[index] = value
                timestamps.append(time.monotonic() - age)
        pose = compute_go2_pose(positions, timestamp=min(timestamps) if timestamps else time.monotonic())
        twist, age = self.twist_reader.get()
        if twist is None or age >= self.timeout:
            return pose
        linear, angular = twist
        return MocapPose(
            position=pose.position,
            rotation=pose.rotation,
            timestamp=pose.timestamp,
            linear_velocity_world=mocap_to_world(linear).astype(np.float32),
            angular_velocity_world=mocap_to_world(angular).astype(np.float32),
        )

    def wait_ready(self, timeout: float = 15.0) -> MocapPose:
        deadline = time.monotonic() + timeout
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                return self.sample()
            except MocapUnavailable as exc:
                last_error = exc
                time.sleep(0.05)
        raise TimeoutError(f"Mocap did not become ready within {timeout:.1f}s: {last_error}")

    def close(self) -> None:
        for reader in self.marker_readers.values():
            reader.close()
        self.twist_reader.close()
