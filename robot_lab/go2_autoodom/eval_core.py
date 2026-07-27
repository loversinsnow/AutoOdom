"""Shared AutoOdom-closed-loop command evaluation for MuJoCo and real Go2."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from .artifacts import atomic_json_dump
from .constants import SAMPLE_DT
from .eval_commands import EvalCommand, command_uses_origin2, compose_pose2d, wrap_to_pi
from .real.low_level import Go2State


@dataclass(frozen=True)
class TruePose:
    position: np.ndarray
    rotation: np.ndarray
    timestamp: float

    @property
    def yaw(self) -> float:
        return float(math.atan2(float(self.rotation[1, 0]), float(self.rotation[0, 0])))

    @property
    def pose2d(self) -> np.ndarray:
        return np.asarray([self.position[0], self.position[1], self.yaw], dtype=np.float32)


class EvaluationBackend(Protocol):
    control_dt: float

    def read_state(self) -> Go2State: ...

    def true_pose(self) -> TruePose: ...

    def apply_action(self, action: np.ndarray, state: Go2State) -> np.ndarray: ...


@dataclass(frozen=True)
class EvaluationConfig:
    average_speed: float = 0.8
    final_speed: float = 0.8
    time_scale: float = 1.01
    success_distance: float = 0.30
    navigation_gain: float = 0.8
    zero_command_steps: int = 10
    return_position_tolerance: float = 0.30
    return_yaw_tolerance: float = math.radians(20.0)
    return_timeout: float = 20.0
    return_gain_xy: float = 0.8
    return_gain_yaw: float = 1.2
    return_max_vx: float = 0.60
    return_max_vy: float = 0.60
    return_max_yaw: float = 0.50
    return_stable_steps: int = 10

    def __post_init__(self) -> None:
        positive = {
            "average_speed": self.average_speed,
            "final_speed": self.final_speed,
            "time_scale": self.time_scale,
            "success_distance": self.success_distance,
            "navigation_gain": self.navigation_gain,
            "return_timeout": self.return_timeout,
        }
        for name, value in positive.items():
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and positive, got {value}")
        if self.zero_command_steps < 0 or self.return_stable_steps < 1:
            raise ValueError("Evaluation step counts are invalid")


def horizontal_basis(rotation: np.ndarray) -> np.ndarray:
    """Return world-from-local XY with +X forward and +Y left."""
    rotation = np.asarray(rotation, dtype=np.float64).reshape(3, 3)
    x_axis = rotation[:2, 0]
    norm = float(np.linalg.norm(x_axis))
    if not np.isfinite(norm) or norm <= 1.0e-8:
        raise ValueError("Robot forward direction cannot define a horizontal frame")
    x_axis = x_axis / norm
    y_axis = np.asarray([-x_axis[1], x_axis[0]], dtype=np.float64)
    return np.column_stack([x_axis, y_axis]).astype(np.float32)


def command_timeout(position: np.ndarray, average_speed: float = 0.8, time_scale: float = 1.01) -> float:
    position = np.asarray(position, dtype=np.float64).reshape(2)
    if average_speed <= 0.0 or time_scale <= 0.0:
        raise ValueError("average_speed and time_scale must be positive")
    return float(np.linalg.norm(position) / max(float(average_speed), 1.0e-6) * float(time_scale))


def navigation_velocity_command(
    estimated_position_world: np.ndarray,
    estimated_goal_world: np.ndarray,
    current_world_from_body: np.ndarray,
    *,
    gain: float = 0.8,
    max_speed: float = 0.8,
) -> np.ndarray:
    """Generate body velocity strictly from AutoOdom state and the estimator-frame goal."""
    estimated_position = np.asarray(estimated_position_world, dtype=np.float32).reshape(3)
    estimated_goal = np.asarray(estimated_goal_world, dtype=np.float32).reshape(3)
    rotation = np.asarray(current_world_from_body, dtype=np.float32).reshape(3, 3)
    error_world = estimated_goal - estimated_position
    error_world[2] = 0.0
    command_xy = (rotation.T @ error_world)[:2] * float(gain)
    speed = float(np.linalg.norm(command_xy))
    if speed > max_speed:
        command_xy *= float(max_speed) / speed
    command = np.asarray([command_xy[0], command_xy[1], 0.0], dtype=np.float32)
    if not np.isfinite(command).all():
        raise RuntimeError("Navigation command contains NaN or infinity")
    return command


def true_goal_position(start_pose: TruePose, local_position: np.ndarray) -> np.ndarray:
    goal = start_pose.position.copy().astype(np.float32)
    goal[:2] += horizontal_basis(start_pose.rotation) @ np.asarray(local_position, dtype=np.float32).reshape(2)
    return goal


def command_succeeded(true_position: np.ndarray, goal_position: np.ndarray, tolerance: float = 0.30) -> bool:
    """Success intentionally ignores heading and checks true horizontal distance only."""
    current = np.asarray(true_position, dtype=np.float64).reshape(3)
    goal = np.asarray(goal_position, dtype=np.float64).reshape(3)
    return float(np.linalg.norm(current[:2] - goal[:2])) < float(tolerance)


def _jsonable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


class CommandEvaluator:
    """Run command episodes while keeping true-pose data out of the navigation controller."""

    def __init__(
        self,
        *,
        backend: EvaluationBackend,
        policy,
        estimator,
        output_dir: str | Path,
        origin2_relative_pose: np.ndarray,
        config: EvaluationConfig | None = None,
    ):
        self.backend = backend
        self.policy = policy
        self.estimator = estimator
        self.output_dir = Path(output_dir).expanduser().resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.trajectory_dir = self.output_dir / "trajectories"
        self.trajectory_dir.mkdir(parents=True, exist_ok=True)
        self.origin2_relative_pose = np.asarray(origin2_relative_pose, dtype=np.float32).reshape(3)
        self.config = config or EvaluationConfig()
        if not np.isclose(float(self.backend.control_dt), SAMPLE_DT):
            raise ValueError(f"Evaluation backend must run at {SAMPLE_DT:.2f}s, got {self.backend.control_dt}")

    def _policy_step(self, command: np.ndarray) -> tuple[Go2State, np.ndarray]:
        state = self.backend.read_state()
        action = self.policy.act(state, command)
        self.backend.apply_action(action, state)
        return state, action

    def _settle_with_zero_command(self) -> None:
        self.policy.reset()
        zero = np.zeros(3, dtype=np.float32)
        for _ in range(self.config.zero_command_steps):
            self._policy_step(zero)
        self.policy.reset()

    def _return_to_pose(self, target_pose2d: np.ndarray) -> bool:
        target = np.asarray(target_pose2d, dtype=np.float32).reshape(3)
        self.policy.reset()
        stable_steps = 0
        max_steps = max(1, int(math.floor(self.config.return_timeout / self.backend.control_dt)))
        for _ in range(max_steps):
            pose = self.backend.true_pose()
            error_world = target[:2] - pose.position[:2]
            rotation = pose.rotation
            error_body = (rotation.T @ np.asarray([error_world[0], error_world[1], 0.0]))[:2]
            yaw_error = wrap_to_pi(float(target[2] - pose.yaw))
            position_error = float(np.linalg.norm(error_world))
            if (
                position_error < self.config.return_position_tolerance
                and abs(yaw_error) < self.config.return_yaw_tolerance
            ):
                stable_steps += 1
                command = np.zeros(3, dtype=np.float32)
                if stable_steps >= self.config.return_stable_steps:
                    self.policy.reset()
                    return True
            else:
                stable_steps = 0
                command = np.asarray(
                    [
                        np.clip(
                            self.config.return_gain_xy * error_body[0],
                            -self.config.return_max_vx,
                            self.config.return_max_vx,
                        ),
                        np.clip(
                            self.config.return_gain_xy * error_body[1],
                            -self.config.return_max_vy,
                            self.config.return_max_vy,
                        ),
                        np.clip(
                            self.config.return_gain_yaw * yaw_error,
                            -self.config.return_max_yaw,
                            self.config.return_max_yaw,
                        ),
                    ],
                    dtype=np.float32,
                )
            self._policy_step(command)
        self.policy.reset()
        return False

    def _run_command(self, command: EvalCommand, command_number: int, origin_name: str) -> dict[str, object]:
        self.policy.reset()
        self.estimator.reset()
        start_state = self.backend.read_state()
        start_pose = self.backend.true_pose()
        true_goal = true_goal_position(start_pose, command.position)
        estimator_goal = np.zeros(3, dtype=np.float32)
        estimator_goal[:2] = horizontal_basis(start_state.rotation) @ command.position
        timeout = command_timeout(
            command.position,
            average_speed=self.config.average_speed,
            time_scale=self.config.time_scale,
        )
        max_steps = max(1, int(math.floor(timeout / self.backend.control_dt)))
        previous_action = np.zeros(12, dtype=np.float32)
        trace = {
            name: []
            for name in (
                "true_position",
                "estimated_position",
                "navigation_command",
                "joint_action",
                "true_distance_to_goal",
            )
        }
        success = False
        steps = 0
        terminal_pose = None

        for step in range(max_steps + 1):
            state = self.backend.read_state()
            _, estimated_position = self.estimator.update(
                joint_pos=state.joint_pos,
                joint_vel=state.joint_vel,
                gyro_ang_vel=state.gyro,
                base_rot_mat=state.rotation,
                joint_commands=previous_action,
                imu_lin_acc=state.acceleration,
            )
            pose = self.backend.true_pose()
            true_distance = float(np.linalg.norm(pose.position[:2] - true_goal[:2]))
            success = command_succeeded(
                pose.position,
                true_goal,
                tolerance=self.config.success_distance,
            )
            velocity_command = (
                np.zeros(3, dtype=np.float32)
                if success or step == max_steps
                else navigation_velocity_command(
                    estimated_position,
                    estimator_goal,
                    state.rotation,
                    gain=self.config.navigation_gain,
                    max_speed=self.config.average_speed,
                )
            )
            trace["true_position"].append(pose.position.copy())
            trace["estimated_position"].append(estimated_position.copy())
            trace["navigation_command"].append(velocity_command.copy())
            trace["joint_action"].append(previous_action.copy())
            trace["true_distance_to_goal"].append(true_distance)
            if success or step == max_steps:
                terminal_pose = pose
                stop_action = self.policy.act(state, np.zeros(3, dtype=np.float32))
                self.backend.apply_action(stop_action, state)
                break
            action = self.policy.act(state, velocity_command)
            self.backend.apply_action(action, state)
            previous_action = action.copy()
            steps += 1

        if terminal_pose is None:
            raise RuntimeError("Evaluation command ended without a terminal pose")
        final_pose = terminal_pose
        estimated_world = np.asarray(trace["estimated_position"][-1], dtype=np.float32)
        true_local = horizontal_basis(start_pose.rotation).T @ (final_pose.position[:2] - start_pose.position[:2])
        estimated_local = horizontal_basis(start_state.rotation).T @ estimated_world[:2]
        true_positions = np.asarray(trace["true_position"], dtype=np.float32)
        true_path_length = float(
            np.linalg.norm(np.diff(true_positions[:, :2], axis=0), axis=1).sum() if len(true_positions) > 1 else 0.0
        )
        trajectory_path = self.trajectory_dir / f"command_{command_number:03d}.npz"
        np.savez_compressed(
            trajectory_path,
            **{name: np.asarray(values, dtype=np.float32) for name, values in trace.items()},
            target_local=np.asarray(command.position, dtype=np.float32),
            true_goal=np.asarray(true_goal, dtype=np.float32),
            estimator_goal=np.asarray(estimator_goal, dtype=np.float32),
            source_line=np.asarray(command.source_index, dtype=np.int32),
            control_dt=np.asarray(self.backend.control_dt, dtype=np.float32),
        )
        result: dict[str, object] = {
            "command_number": command_number,
            "source_line": command.source_index,
            "origin": origin_name,
            "target_local_xy": command.position,
            "timeout_s": timeout,
            "elapsed_s": steps * self.backend.control_dt,
            "steps": steps,
            "success": success,
            "timed_out": not success,
            "final_true_distance_m": float(np.linalg.norm(final_pose.position[:2] - true_goal[:2])),
            "true_local_displacement_xy": true_local,
            "estimated_local_displacement_xy": estimated_local,
            "odometry_endpoint_error_m": float(np.linalg.norm(estimated_local - true_local)),
            "true_path_length_m": true_path_length,
            "trajectory_file": str(trajectory_path.relative_to(self.output_dir)),
        }
        return _jsonable(result)

    @staticmethod
    def _summary(results: Sequence[dict[str, object]], aborted_reason: str | None) -> dict[str, object]:
        completed = len(results)
        successes = sum(bool(result["success"]) for result in results)
        final_distances = [float(result["final_true_distance_m"]) for result in results]
        odometry_errors = [float(result["odometry_endpoint_error_m"]) for result in results]
        return {
            "completed_commands": completed,
            "successful_commands": successes,
            "failed_commands": completed - successes,
            "success_rate": successes / completed if completed else 0.0,
            "mean_final_true_distance_m": float(np.mean(final_distances)) if final_distances else None,
            "mean_odometry_endpoint_error_m": float(np.mean(odometry_errors)) if odometry_errors else None,
            "total_commanded_distance_m": float(sum(np.linalg.norm(result["target_local_xy"]) for result in results)),
            "total_true_path_length_m": float(sum(float(result["true_path_length_m"]) for result in results)),
            "aborted": aborted_reason is not None,
            "aborted_reason": aborted_reason,
        }

    def run(self, commands: Sequence[EvalCommand], metadata: dict[str, object]) -> dict[str, object]:
        if not commands:
            raise ValueError("At least one evaluation command is required")
        metadata_payload = {
            **_jsonable(metadata),
            "evaluation_config": _jsonable(asdict(self.config)),
            "command_count": len(commands),
            "ground_truth_use": "success_metrics_and_auto_return_only",
            "navigation_feedback": "autoodom_closed_loop",
            "success_definition": "true_xy_distance_m < success_distance; heading ignored",
            "timeout_definition": "norm(target_local_xy) / average_speed * time_scale",
            "warm_start": False,
        }
        atomic_json_dump(metadata_payload, self.output_dir / "evaluation_config.json")

        origin1 = self.backend.true_pose().pose2d
        origin2 = compose_pose2d(origin1, self.origin2_relative_pose)
        origins = {"origin_1": origin1, "origin_2": origin2}
        results: list[dict[str, object]] = []
        aborted_reason = None
        progress_path = self.output_dir / "progress.json"

        try:
            first_origin = "origin_2" if command_uses_origin2(commands[0]) else "origin_1"
            self._settle_with_zero_command()
            if first_origin == "origin_2" and not self._return_to_pose(origin2):
                aborted_reason = "Initial auto-return to origin_2 timed out"
            for index, command in enumerate(commands):
                if aborted_reason is not None:
                    break
                origin_name = "origin_2" if command_uses_origin2(command) else "origin_1"
                print(
                    f"[Eval] command {index + 1}/{len(commands)} line={command.source_index} "
                    f"origin={origin_name} pos=[{command.position[0]:+.3f}, {command.position[1]:+.3f}]"
                )
                result = self._run_command(command, index + 1, origin_name)
                results.append(result)
                print(
                    f"[Eval] {'SUCCESS' if result['success'] else 'TIMEOUT'} "
                    f"distance={result['final_true_distance_m']:.3f}m "
                    f"elapsed={result['elapsed_s']:.2f}s"
                )
                atomic_json_dump(
                    {
                        "metadata": metadata_payload,
                        "origins": _jsonable(origins),
                        "results": results,
                        "summary": self._summary(results, aborted_reason),
                    },
                    progress_path,
                )
                self._settle_with_zero_command()
                next_origin = (
                    "origin_2"
                    if index + 1 < len(commands) and command_uses_origin2(commands[index + 1])
                    else "origin_1"
                )
                if not self._return_to_pose(origins[next_origin]):
                    aborted_reason = f"Auto-return to {next_origin} timed out after command {index + 1}"
                    break
        except BaseException as exc:
            aborted_reason = f"{type(exc).__name__}: {exc}"
            atomic_json_dump(
                {
                    "metadata": metadata_payload,
                    "origins": _jsonable(origins),
                    "results": results,
                    "summary": self._summary(results, aborted_reason),
                },
                progress_path,
            )
            raise

        payload = {
            "metadata": metadata_payload,
            "origins": _jsonable(origins),
            "results": results,
            "summary": self._summary(results, aborted_reason),
        }
        atomic_json_dump(payload, progress_path)
        atomic_json_dump(payload, self.output_dir / "summary.json")
        return payload
