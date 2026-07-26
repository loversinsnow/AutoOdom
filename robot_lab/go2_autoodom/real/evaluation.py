"""Mocap-ground-truth backend for safety-gated real Go2 command evaluation."""

from __future__ import annotations

import time

import numpy as np

from ..constants import SAMPLE_DT
from ..eval_core import TruePose
from .low_level import Go2LowLevelInterface, Go2State
from .mocap import MocapTracker


class RealGo2EvaluationBackend:
    control_dt = SAMPLE_DT

    def __init__(self, controller: Go2LowLevelInterface, mocap: MocapTracker):
        self.controller = controller
        self.mocap = mocap
        self._next_tick: float | None = None

    def reset_timing(self) -> None:
        self._next_tick = None

    def read_state(self) -> Go2State:
        return self.controller.read_state()

    def true_pose(self) -> TruePose:
        pose = self.mocap.sample()
        return TruePose(
            position=pose.position.copy(),
            rotation=pose.rotation.copy(),
            timestamp=pose.timestamp,
        )

    def apply_action(self, action: np.ndarray, state: Go2State) -> np.ndarray:
        now = time.monotonic()
        if self._next_tick is None:
            self._next_tick = now + self.control_dt
        else:
            self._next_tick += self.control_dt
            if now - self._next_tick > 0.10:
                raise TimeoutError("Real Go2 control loop was delayed by more than 0.10s")
        applied = self.controller.send_policy_action(action, state)
        remaining = self._next_tick - time.monotonic()
        if remaining > 0.0:
            time.sleep(remaining)
        return applied

