"""Train the repository-local Go2 locomotion policy with Isaac Lab 2.1/RSL-RL 2.3.1."""

from __future__ import annotations

import argparse
from pathlib import Path

from isaaclab.app import AppLauncher

from .artifacts import SIMULATION_LOG_ROOT
from .constants import TASK_ID


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", default=TASK_ID)
parser.add_argument("--num-envs", type=int, default=None)
parser.add_argument("--max-iterations", type=int, default=None)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--output-root", type=Path, default=SIMULATION_LOG_ROOT)
parser.add_argument("--resume-checkpoint", type=Path)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()

app_launcher = AppLauncher(args)
simulation_app = app_launcher.app

import gymnasium as gym
import torch
from rsl_rl.runners import OnPolicyRunner

from isaaclab.utils.io import dump_pickle, dump_yaml
from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper, export_policy_as_jit
from isaaclab_tasks.utils import parse_env_cfg
from isaaclab_tasks.utils.parse_cfg import load_cfg_from_registry

from . import isaaclab_task  # noqa: F401, E402
from .artifacts import create_timestamped_run, exported_dir, update_run_manifest
from .deployment import write_deployment_manifest
from .policy_quality import validate_policy_actions


def main() -> None:
    env_cfg = parse_env_cfg(args.task, device=args.device, num_envs=args.num_envs)
    agent_cfg = load_cfg_from_registry(args.task, "rsl_rl_cfg_entry_point")
    agent_cfg.seed = args.seed
    agent_cfg.device = args.device
    if args.max_iterations is not None:
        agent_cfg.max_iterations = args.max_iterations
    env_cfg.seed = args.seed
    env_cfg.sim.device = args.device

    log_dir = create_timestamped_run(args.output_root)
    print(f"[INFO] Logging experiment in: {log_dir}")

    env = gym.make(args.task, cfg=env_cfg)
    wrapped_env = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    runner = OnPolicyRunner(wrapped_env, agent_cfg.to_dict(), log_dir=str(log_dir), device=agent_cfg.device)
    if args.resume_checkpoint is not None:
        checkpoint = args.resume_checkpoint.expanduser().resolve()
        if not checkpoint.is_file():
            raise FileNotFoundError(checkpoint)
        runner.load(str(checkpoint))
    dump_yaml(str(log_dir / "params" / "env.yaml"), env_cfg)
    dump_yaml(str(log_dir / "params" / "agent.yaml"), agent_cfg)
    dump_pickle(str(log_dir / "params" / "env.pkl"), env_cfg)
    dump_pickle(str(log_dir / "params" / "agent.pkl"), agent_cfg)
    runner.learn(num_learning_iterations=agent_cfg.max_iterations, init_at_random_ep_len=True)

    observations, _ = wrapped_env.get_observations()
    inference_policy = runner.get_inference_policy(device=agent_cfg.device)
    with torch.inference_mode():
        action_stats = validate_policy_actions(
            inference_policy(observations),
            context="Trained locomotion policy",
        )
    print(
        f"[INFO] Policy action preflight: max_abs={action_stats.max_abs:.3f}, "
        f"outside_unit_range={action_stats.outside_unit_range_fraction:.1%}"
    )

    try:
        policy_module = runner.alg.policy
    except AttributeError:
        policy_module = runner.alg.actor_critic
    deployment_dir = exported_dir(log_dir)
    export_policy_as_jit(
        policy_module,
        runner.obs_normalizer,
        path=str(deployment_dir),
        filename="policy.pt",
    )
    write_deployment_manifest(deployment_dir / "deployment.json", "policy.pt")
    update_run_manifest(
        log_dir,
        stage=1,
        training_domain="simulation",
        extra={
            "policy_training": "isaac_lab_rsl_rl",
            "control_policy_origin": "trained_in_simulation",
        },
    )
    print(f"[SUCCESS] Control policy: {(deployment_dir / 'policy.pt').resolve()}")
    env.close()


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
