"""Isaac Lab 2.1 task configuration with deployable Go2 observations."""

from __future__ import annotations

from isaaclab.managers import SceneEntityCfg
from isaaclab.utils import configclass
from isaaclab_tasks.manager_based.locomotion.velocity.config.go2.flat_env_cfg import (
    UnitreeGo2FlatEnvCfg,
    UnitreeGo2FlatEnvCfg_PLAY,
)

from ..constants import GO2_JOINT_NAMES


def _apply_autoodom_go2_contract(config: UnitreeGo2FlatEnvCfg) -> None:
    # The real Go2 cannot observe base linear velocity; never train the policy with it.
    config.observations.policy.base_lin_vel = None
    config.observations.policy.height_scan = None
    joint_selector = SceneEntityCfg(
        "robot",
        joint_names=list(GO2_JOINT_NAMES),
        preserve_order=True,
    )
    config.observations.policy.joint_pos.params["asset_cfg"] = joint_selector
    config.observations.policy.joint_vel.params["asset_cfg"] = SceneEntityCfg(
        "robot",
        joint_names=list(GO2_JOINT_NAMES),
        preserve_order=True,
    )

    config.actions.joint_pos.joint_names = list(GO2_JOINT_NAMES)
    config.actions.joint_pos.preserve_order = True
    config.actions.joint_pos.scale = {
        ".*_hip_joint": 0.125,
        ".*_(thigh|calf)_joint": 0.25,
    }
    config.actions.joint_pos.clip = {".*": (-1.0, 1.0)}
    config.actions.joint_pos.use_default_offset = True

    # 200 Hz physics with decimation 4 gives the shared 50 Hz control/data rate.
    config.sim.dt = 0.005
    config.decimation = 4


@configclass
class AutoOdomGo2FlatEnvCfg(UnitreeGo2FlatEnvCfg):
    def __post_init__(self) -> None:
        super().__post_init__()
        _apply_autoodom_go2_contract(self)


@configclass
class AutoOdomGo2FlatEnvCfg_PLAY(UnitreeGo2FlatEnvCfg_PLAY):
    def __post_init__(self) -> None:
        super().__post_init__()
        _apply_autoodom_go2_contract(self)
        self.scene.num_envs = 1
        self.observations.policy.enable_corruption = False
