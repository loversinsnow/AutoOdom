"""RSL-RL 2.3.1 configuration for the Go2 locomotion policy."""

from isaaclab.utils import configclass
from isaaclab_tasks.manager_based.locomotion.velocity.config.go2.agents.rsl_rl_ppo_cfg import (
    UnitreeGo2FlatPPORunnerCfg,
)


@configclass
class AutoOdomGo2FlatPPORunnerCfg(UnitreeGo2FlatPPORunnerCfg):
    def __post_init__(self) -> None:
        super().__post_init__()
        self.experiment_name = "go2_autoodom_flat"
        self.max_iterations = 1500
        self.save_interval = 50
        self.seed = 42
        # Do not hide the sampled Gaussian actions from the environment/reward
        # terms. Clipping here lets PPO increase its entropy indefinitely while
        # every large action has the same effect after clipping.
        self.clip_actions = None
