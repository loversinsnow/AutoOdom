"""Standalone MuJoCo 200 Hz / Go2 policy 50 Hz evaluation backend."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from .constants import (
    GO2_DEFAULT_JOINT_POS,
    GO2_D_GAINS,
    GO2_JOINT_NAMES,
    GO2_P_GAINS,
    GO2_TORQUE_LIMITS,
    PACKAGE_DIR,
    SAMPLE_DT,
)
from .eval_core import TruePose
from .real.low_level import Go2State, safe_policy_targets
from .real.remote import parse_remote


DEFAULT_MUJOCO_XML = PACKAGE_DIR / "assets" / "go2_mujoco.xml"


class MujocoGo2Backend:
    """Primitive-geometry Go2 model built from this repository's local URDF contract."""

    control_dt = SAMPLE_DT

    def __init__(
        self,
        xml_path: str | Path = DEFAULT_MUJOCO_XML,
        *,
        viewer: bool = False,
        realtime: bool = False,
    ):
        try:
            import mujoco
        except ImportError as exc:
            raise RuntimeError(
                "MuJoCo is unavailable in the active environment; no package installation was attempted"
            ) from exc

        self.mujoco = mujoco
        self.xml_path = Path(xml_path).expanduser().resolve()
        if not self.xml_path.is_file():
            raise FileNotFoundError(self.xml_path)
        self.model = mujoco.MjModel.from_xml_path(str(self.xml_path))
        self.data = mujoco.MjData(self.model)
        self.realtime = bool(realtime)
        if not np.isclose(float(self.model.opt.timestep), 0.005):
            raise ValueError(f"MuJoCo physics timestep must be 0.005s, got {self.model.opt.timestep}")
        self.physics_steps = int(round(self.control_dt / float(self.model.opt.timestep)))
        if not np.isclose(self.physics_steps * float(self.model.opt.timestep), self.control_dt):
            raise ValueError("MuJoCo physics timestep does not divide the 50 Hz control interval")

        self.base_body_id = self._name_id(mujoco.mjtObj.mjOBJ_BODY, "base")
        self.joint_ids = np.asarray(
            [self._name_id(mujoco.mjtObj.mjOBJ_JOINT, name) for name in GO2_JOINT_NAMES],
            dtype=np.int32,
        )
        self.qpos_indices = np.asarray(self.model.jnt_qposadr[self.joint_ids], dtype=np.int32)
        self.dof_indices = np.asarray(self.model.jnt_dofadr[self.joint_ids], dtype=np.int32)
        self.actuator_ids = np.asarray(
            [
                self._name_id(mujoco.mjtObj.mjOBJ_ACTUATOR, f"motor_{name.removesuffix('_joint')}")
                for name in GO2_JOINT_NAMES
            ],
            dtype=np.int32,
        )
        self.gyro_sensor_id = self._name_id(mujoco.mjtObj.mjOBJ_SENSOR, "imu_gyro")
        self.acceleration_sensor_id = self._name_id(
            mujoco.mjtObj.mjOBJ_SENSOR,
            "imu_accelerometer",
        )
        self._viewer = None
        if viewer:
            import mujoco.viewer

            self._viewer = mujoco.viewer.launch_passive(self.model, self.data)
        self.reset()

    def _name_id(self, object_type, name: str) -> int:
        identifier = int(self.mujoco.mj_name2id(self.model, object_type, name))
        if identifier < 0:
            raise ValueError(f"MuJoCo model is missing {name!r}")
        return identifier

    def _sensor(self, sensor_id: int) -> np.ndarray:
        start = int(self.model.sensor_adr[sensor_id])
        dimension = int(self.model.sensor_dim[sensor_id])
        return np.asarray(self.data.sensordata[start : start + dimension], dtype=np.float32).copy()

    def reset(self) -> None:
        self.mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[self.qpos_indices] = GO2_DEFAULT_JOINT_POS
        self.data.qvel[:] = 0.0
        self.mujoco.mj_forward(self.model, self.data)
        self._sync_viewer()

    def _joint_state(self) -> tuple[np.ndarray, np.ndarray]:
        return (
            np.asarray(self.data.qpos[self.qpos_indices], dtype=np.float32).copy(),
            np.asarray(self.data.qvel[self.dof_indices], dtype=np.float32).copy(),
        )

    def _set_pd_target(self, target_position: np.ndarray) -> None:
        joint_pos, joint_vel = self._joint_state()
        torque = GO2_P_GAINS * (np.asarray(target_position, dtype=np.float32) - joint_pos)
        torque -= GO2_D_GAINS * joint_vel
        self.data.ctrl[self.actuator_ids] = np.clip(torque, -GO2_TORQUE_LIMITS, GO2_TORQUE_LIMITS)

    def _sync_viewer(self) -> None:
        if self._viewer is not None:
            if not self._viewer.is_running():
                raise KeyboardInterrupt("MuJoCo viewer was closed")
            self._viewer.sync()

    def settle(self, duration: float = 2.0) -> None:
        """Let the local model reach its default standing pose before evaluation."""
        physics_steps = max(1, int(round(float(duration) / float(self.model.opt.timestep))))
        for _ in range(physics_steps):
            self._set_pd_target(GO2_DEFAULT_JOINT_POS)
            self.mujoco.mj_step(self.model, self.data)
            if self._viewer is not None and int(self.data.time / self.model.opt.timestep) % 4 == 0:
                self._sync_viewer()
        if not np.isfinite(np.concatenate([self.data.qpos, self.data.qvel])).all():
            raise RuntimeError("MuJoCo state became non-finite while settling")

    def read_state(self) -> Go2State:
        joint_pos, joint_vel = self._joint_state()
        quaternion = np.asarray(self.data.xquat[self.base_body_id], dtype=np.float32).copy()
        rotation = np.asarray(self.data.xmat[self.base_body_id], dtype=np.float32).reshape(3, 3).copy()
        state = Go2State(
            joint_pos=joint_pos,
            joint_vel=joint_vel,
            joint_torque=np.asarray(self.data.actuator_force[self.actuator_ids], dtype=np.float32).copy(),
            gyro=self._sensor(self.gyro_sensor_id),
            acceleration=self._sensor(self.acceleration_sensor_id),
            quaternion_wxyz=quaternion,
            rotation=rotation,
            remote=parse_remote(bytes(24)),
            timestamp=float(self.data.time),
        )
        values = np.concatenate(
            [
                state.joint_pos,
                state.joint_vel,
                state.joint_torque,
                state.gyro,
                state.acceleration,
                state.quaternion_wxyz,
            ]
        )
        if not np.isfinite(values).all():
            raise RuntimeError("MuJoCo Go2 state contains NaN or infinity")
        if float(self.data.xpos[self.base_body_id, 2]) < 0.12:
            raise RuntimeError("MuJoCo Go2 base fell below the protected height")
        return state

    def true_pose(self) -> TruePose:
        return TruePose(
            position=np.asarray(self.data.xpos[self.base_body_id], dtype=np.float32).copy(),
            rotation=np.asarray(self.data.xmat[self.base_body_id], dtype=np.float32).reshape(3, 3).copy(),
            timestamp=float(self.data.time),
        )

    def apply_action(self, action: np.ndarray, state: Go2State) -> np.ndarray:
        start_time = time.monotonic()
        applied_action, target_position = safe_policy_targets(
            action,
            state.joint_pos,
            state.joint_vel,
        )
        for _ in range(self.physics_steps):
            self._set_pd_target(target_position)
            self.mujoco.mj_step(self.model, self.data)
        self._sync_viewer()
        if self.realtime:
            remaining = self.control_dt - (time.monotonic() - start_time)
            if remaining > 0.0:
                time.sleep(remaining)
        return applied_action

    def close(self) -> None:
        if self._viewer is not None:
            self._viewer.close()
            self._viewer = None

