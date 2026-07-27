"""Safety-gated Unitree SDK2 low-level interface for Go2."""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..constants import (
    DEFAULT_UNITREE_SDK_DIR,
    GO2_ACTION_SCALE,
    GO2_DDS_MOTOR_INDICES,
    GO2_DDS_SIGNS,
    GO2_DEFAULT_JOINT_POS,
    GO2_D_GAINS,
    GO2_JOINT_LIMIT_HIGH,
    GO2_JOINT_LIMIT_LOW,
    GO2_P_GAINS,
    GO2_TORQUE_LIMITS,
    SAMPLE_DT,
)
from ..math_utils import rotation_matrix_from_wxyz
from .remote import RemoteButtons, RemoteState, parse_remote


@dataclass(frozen=True)
class Go2State:
    joint_pos: np.ndarray
    joint_vel: np.ndarray
    joint_torque: np.ndarray
    gyro: np.ndarray
    acceleration: np.ndarray
    quaternion_wxyz: np.ndarray
    rotation: np.ndarray
    remote: RemoteState
    timestamp: float


def safe_policy_targets(
    action: np.ndarray,
    joint_pos: np.ndarray,
    joint_vel: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Map a raw policy action to targets bounded by PD torque and physical joint limits."""
    raw = np.asarray(action, dtype=np.float32).reshape(12)
    joint_pos = np.asarray(joint_pos, dtype=np.float32).reshape(12)
    joint_vel = np.asarray(joint_vel, dtype=np.float32).reshape(12)
    if not np.isfinite(np.concatenate([raw, joint_pos, joint_vel])).all():
        raise ValueError("Policy action and joint state must be finite")
    desired_targets = GO2_DEFAULT_JOINT_POS + raw * GO2_ACTION_SCALE
    torque_target_low = joint_pos + (-GO2_TORQUE_LIMITS + GO2_D_GAINS * joint_vel) / GO2_P_GAINS
    torque_target_high = joint_pos + (GO2_TORQUE_LIMITS + GO2_D_GAINS * joint_vel) / GO2_P_GAINS
    target_low = np.maximum(GO2_JOINT_LIMIT_LOW, torque_target_low)
    target_high = np.minimum(GO2_JOINT_LIMIT_HIGH, torque_target_high)
    if np.any(target_low > target_high):
        raise ValueError("Current joint state has no target satisfying both torque and position limits")
    targets = np.clip(desired_targets, target_low, target_high)
    applied_action = (targets - GO2_DEFAULT_JOINT_POS) / GO2_ACTION_SCALE
    return applied_action.astype(np.float32), targets.astype(np.float32)


def _load_sdk(sdk_path: str | Path):
    path = Path(sdk_path).expanduser().resolve()
    if not (path / "unitree_sdk2py").is_dir():
        raise RuntimeError(
            f"Unitree SDK2 Python was not found at {path}. Pass --unitree-sdk-path without installing it into Conda."
        )
    if str(path) not in sys.path:
        sys.path.append(str(path))
    try:
        from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelPublisher, ChannelSubscriber
        from unitree_sdk2py.idl.default import unitree_go_msg_dds__LowCmd_
        from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowCmd_, LowState_
        from unitree_sdk2py.utils.crc import CRC
    except Exception as exc:
        raise RuntimeError(f"Failed to import Unitree SDK2 Python from {path}") from exc
    return (
        ChannelFactoryInitialize,
        ChannelPublisher,
        ChannelSubscriber,
        unitree_go_msg_dds__LowCmd_,
        LowCmd_,
        LowState_,
        CRC,
    )


def stop_sport_mode(
    network_interface: str,
    *,
    sdk_path: str | Path = DEFAULT_UNITREE_SDK_DIR,
    initialize_channel: bool = True,
) -> None:
    channel_initialize, *_ = _load_sdk(sdk_path)
    from unitree_sdk2py.go2.robot_state.robot_state_client import RobotStateClient

    if initialize_channel:
        channel_initialize(0, network_interface)
    client = RobotStateClient()
    client.SetTimeout(3.0)
    client.Init()
    result = client.ServiceSwitch("sport_mode", False)
    if result != 0:
        raise RuntimeError(f"Failed to disable sport_mode: Unitree error code {result}")


class Go2LowLevelInterface:
    def __init__(
        self,
        *,
        network_interface: str,
        live: bool = False,
        sdk_path: str | Path = DEFAULT_UNITREE_SDK_DIR,
        state_timeout: float = 0.10,
    ):
        if live and not network_interface:
            raise ValueError("Live control requires an explicit network interface")
        (
            channel_initialize,
            publisher_type,
            subscriber_type,
            default_command,
            low_command_type,
            low_state_type,
            crc_type,
        ) = _load_sdk(sdk_path)
        channel_initialize(0, network_interface)
        self.live = bool(live)
        self.state_timeout = float(state_timeout)
        self._state_message = None
        self._state_timestamp = 0.0
        self._lock = threading.Lock()
        self._estop = threading.Event()
        self._joint_safety_armed = False
        self._crc = crc_type()
        self._command = default_command()
        topic = "rt/lowcmd" if live else f"rt/lowcmd_dryrun_{np.random.randint(0, 65536):04x}"
        self.command_topic = topic
        self._publisher = publisher_type(topic, low_command_type)
        self._publisher.Init()
        self._subscriber = subscriber_type("rt/lowstate", low_state_type)
        self._subscriber.Init(self._on_state, 10)
        print(f"[Go2] low-level interface live={self.live}, command_topic={self.command_topic}")

    @property
    def emergency_stopped(self) -> bool:
        return self._estop.is_set()

    def _on_state(self, message) -> None:
        with self._lock:
            self._state_message = message
            self._state_timestamp = time.monotonic()
        remote = parse_remote(getattr(message, "wireless_remote", []))
        if remote.emergency_stop and not self._estop.is_set():
            self._estop.set()
            self.motor_off()

    def wait_for_state(self, timeout: float = 5.0) -> Go2State:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                return self.read_state()
            except TimeoutError:
                time.sleep(0.005)
        raise TimeoutError(f"No fresh rt/lowstate received within {timeout:.1f}s")

    def read_state(self) -> Go2State:
        with self._lock:
            message = self._state_message
            timestamp = self._state_timestamp
        if message is None or time.monotonic() - timestamp > self.state_timeout:
            raise TimeoutError("rt/lowstate is stale")
        imu = message.imu_state
        quaternion = np.asarray(imu.quaternion, dtype=np.float32).reshape(4)
        state = Go2State(
            joint_pos=np.asarray(
                [message.motor_state[GO2_DDS_MOTOR_INDICES[index]].q * GO2_DDS_SIGNS[index] for index in range(12)],
                dtype=np.float32,
            ),
            joint_vel=np.asarray(
                [message.motor_state[GO2_DDS_MOTOR_INDICES[index]].dq * GO2_DDS_SIGNS[index] for index in range(12)],
                dtype=np.float32,
            ),
            joint_torque=np.asarray(
                [
                    message.motor_state[GO2_DDS_MOTOR_INDICES[index]].tau_est * GO2_DDS_SIGNS[index]
                    for index in range(12)
                ],
                dtype=np.float32,
            ),
            gyro=np.asarray(imu.gyroscope, dtype=np.float32).reshape(3),
            acceleration=np.asarray(imu.accelerometer, dtype=np.float32).reshape(3),
            quaternion_wxyz=quaternion,
            rotation=rotation_matrix_from_wxyz(quaternion),
            remote=parse_remote(getattr(message, "wireless_remote", [])),
            timestamp=timestamp,
        )
        values = np.concatenate([
            state.joint_pos,
            state.joint_vel,
            state.gyro,
            state.acceleration,
            state.quaternion_wxyz,
        ])
        if not np.isfinite(values).all():
            self.motor_off()
            raise RuntimeError("Non-finite value received from Go2 LowState")
        if self._joint_safety_armed:
            midpoint = (GO2_JOINT_LIMIT_LOW + GO2_JOINT_LIMIT_HIGH) / 2.0
            half_range = (GO2_JOINT_LIMIT_HIGH - GO2_JOINT_LIMIT_LOW) / 2.0
            low = midpoint - 1.2 * half_range
            high = midpoint + 1.2 * half_range
            if np.any(state.joint_pos < low) or np.any(state.joint_pos > high):
                self.motor_off()
                raise RuntimeError("Measured Go2 joint position exceeded the protected range")
        return state

    def _write_targets(self, target_pos: np.ndarray) -> None:
        target_pos = np.asarray(target_pos, dtype=np.float32).reshape(12)
        for canonical_index, dds_index in enumerate(GO2_DDS_MOTOR_INDICES):
            motor = self._command.motor_cmd[dds_index]
            motor.mode = 0x01
            motor.q = float(target_pos[canonical_index] * GO2_DDS_SIGNS[canonical_index])
            motor.dq = 0.0
            motor.kp = float(GO2_P_GAINS[canonical_index])
            motor.kd = float(GO2_D_GAINS[canonical_index])
            motor.tau = 0.0
        self._command.crc = self._crc.Crc(self._command)
        self._publisher.Write(self._command)

    def send_policy_action(self, action: np.ndarray, state: Go2State | None = None) -> np.ndarray:
        if self.emergency_stopped:
            raise RuntimeError("Emergency stop is active")
        state = self.read_state() if state is None else state
        try:
            applied_action, targets = safe_policy_targets(action, state.joint_pos, state.joint_vel)
        except ValueError as exc:
            self.motor_off()
            raise RuntimeError(str(exc)) from exc
        self._write_targets(targets)
        return applied_action

    def stand_ramp(self, duration: float = 2.0, max_target_step: float = 0.015) -> None:
        self._joint_safety_armed = False
        initial = self.wait_for_state().joint_pos
        steps = max(1, int(round(duration / SAMPLE_DT)))
        previous = initial.copy()
        for step in range(steps):
            state = self.read_state()
            ratio = float(step + 1) / float(steps)
            desired = initial + ratio * (GO2_DEFAULT_JOINT_POS - initial)
            desired = previous + np.clip(desired - previous, -max_target_step, max_target_step)
            requested_action = (desired - GO2_DEFAULT_JOINT_POS) / GO2_ACTION_SCALE
            applied_action = self.send_policy_action(requested_action, state)
            previous = GO2_DEFAULT_JOINT_POS + applied_action * GO2_ACTION_SCALE
            time.sleep(SAMPLE_DT)

    def wait_for_r1(self) -> None:
        print("[Go2] Holding stand. Press R1 to arm policy control; R2/L2 is emergency stop.")
        previous_pressed = bool(self.read_state().remote.buttons & RemoteButtons.R1)
        while True:
            state = self.read_state()
            self.send_policy_action(np.zeros(12, dtype=np.float32), state)
            pressed = bool(state.remote.buttons & RemoteButtons.R1)
            if pressed and not previous_pressed:
                self._joint_safety_armed = True
                return
            previous_pressed = pressed
            time.sleep(SAMPLE_DT)

    def prepare_for_policy(self) -> None:
        self.stand_ramp()
        self.wait_for_r1()

    def motor_off(self) -> None:
        try:
            for dds_index in GO2_DDS_MOTOR_INDICES:
                motor = self._command.motor_cmd[dds_index]
                motor.mode = 0x00
                motor.q = 0.0
                motor.dq = 0.0
                motor.kp = 0.0
                motor.kd = 0.0
                motor.tau = 0.0
            self._command.crc = self._crc.Crc(self._command)
            self._publisher.Write(self._command)
        except Exception:
            pass

    def shutdown(self) -> None:
        if not self.emergency_stopped:
            try:
                for _ in range(10):
                    state = self.read_state()
                    self.send_policy_action(np.zeros(12, dtype=np.float32), state)
                    time.sleep(SAMPLE_DT)
            except Exception:
                pass
        self.motor_off()
