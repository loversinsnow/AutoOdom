"""Gym registration kept separate from the repository's newer incompatible tasks."""

from __future__ import annotations

import gymnasium as gym

from ..constants import PLAY_TASK_ID, TASK_ID


def register_tasks() -> None:
    registrations = {
        TASK_ID: "AutoOdomGo2FlatEnvCfg",
        PLAY_TASK_ID: "AutoOdomGo2FlatEnvCfg_PLAY",
    }
    for task_id, config_class in registrations.items():
        if task_id in gym.registry:
            continue
        gym.register(
            id=task_id,
            entry_point="isaaclab.envs:ManagerBasedRLEnv",
            disable_env_checker=True,
            kwargs={
                "env_cfg_entry_point": (
                    f"go2_autoodom.isaaclab_task.task_cfg:{config_class}"
                ),
                "rsl_rl_cfg_entry_point": (
                    "go2_autoodom.isaaclab_task.rsl_rl_cfg:AutoOdomGo2FlatPPORunnerCfg"
                ),
            },
        )
