"""Unitree wireless remote decoding and velocity-command mapping."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntFlag

import numpy as np


class RemoteButtons(IntFlag):
    R1 = 1 << 0
    L1 = 1 << 1
    START = 1 << 2
    SELECT = 1 << 3
    R2 = 1 << 4
    L2 = 1 << 5
    F1 = 1 << 6
    F2 = 1 << 7
    A = 1 << 8
    B = 1 << 9
    X = 1 << 10
    Y = 1 << 11
    UP = 1 << 12
    RIGHT = 1 << 13
    DOWN = 1 << 14
    LEFT = 1 << 15


@dataclass(frozen=True)
class RemoteState:
    buttons: RemoteButtons
    left_x: float
    left_y: float
    right_x: float
    right_y: float

    @property
    def emergency_stop(self) -> bool:
        return bool(self.buttons & (RemoteButtons.R2 | RemoteButtons.L2))

    def velocity_command(
        self,
        *,
        max_forward: float = 1.0,
        max_lateral: float = 0.5,
        max_yaw: float = 1.0,
        deadband: float = 0.08,
    ) -> np.ndarray:
        axes = np.asarray([self.left_y, -self.left_x, -self.right_x], dtype=np.float32)
        axes[np.abs(axes) < deadband] = 0.0
        return axes * np.asarray([max_forward, max_lateral, max_yaw], dtype=np.float32)


def parse_remote(data: bytes | bytearray | list[int]) -> RemoteState:
    raw = bytes(data)
    if len(raw) < 24:
        return RemoteState(RemoteButtons(0), 0.0, 0.0, 0.0, 0.0)
    buttons = RemoteButtons(struct.unpack_from("<H", raw, 2)[0])
    left_x = struct.unpack_from("<f", raw, 4)[0]
    right_x = struct.unpack_from("<f", raw, 8)[0]
    right_y = struct.unpack_from("<f", raw, 12)[0]
    left_y = struct.unpack_from("<f", raw, 20)[0]
    axes = [left_x, left_y, right_x, right_y]
    axes = [float(np.clip(value, -1.0, 1.0)) if np.isfinite(value) else 0.0 for value in axes]
    return RemoteState(buttons, axes[0], axes[1], axes[2], axes[3])
