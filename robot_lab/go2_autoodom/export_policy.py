"""Load an RSL-RL checkpoint and export a Go2 TorchScript deployment bundle."""

from __future__ import annotations

import argparse
from pathlib import Path

from isaaclab.app import AppLauncher

from .constants import PLAY_TASK_ID


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--checkpoint", type=Path)
parser.add_argument("--task", default=PLAY_TASK_ID)
parser.add_argument(
    "--output-dir",
    type=Path,
    help="Defaults to <checkpoint-run>/exported, matching the deployment layout",
)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
if args.checkpoint is None:
    parser.error("--checkpoint is required")

app_launcher = AppLauncher(args)
simulation_app = app_launcher.app

import gymnasium as gym
from rsl_rl.runners import OnPolicyRunner

from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper, export_policy_as_jit
from isaaclab_tasks.utils import parse_env_cfg
from isaaclab_tasks.utils.parse_cfg import load_cfg_from_registry

from . import isaaclab_task  # noqa: F401, E402
from .artifacts import exported_dir, update_run_manifest
from .deployment import write_deployment_manifest


def main() -> None:
    checkpoint = args.checkpoint.expanduser().resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    run_dir = checkpoint.parent
    output_dir = args.output_dir.expanduser().resolve() if args.output_dir else exported_dir(run_dir)
    env_cfg = parse_env_cfg(args.task, device=args.device, num_envs=1)
    env_cfg.observations.policy.enable_corruption = False
    agent_cfg = load_cfg_from_registry(args.task, "rsl_rl_cfg_entry_point")
    agent_cfg.device = args.device
    env = gym.make(args.task, cfg=env_cfg)
    wrapped_env = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    runner = OnPolicyRunner(wrapped_env, agent_cfg.to_dict(), log_dir=None, device=agent_cfg.device)
    runner.load(str(checkpoint))
    try:
        policy_module = runner.alg.policy
    except AttributeError:
        policy_module = runner.alg.actor_critic
    output_dir.mkdir(parents=True, exist_ok=True)
    export_policy_as_jit(
        policy_module,
        runner.obs_normalizer,
        path=str(output_dir),
        filename="policy.pt",
    )
    write_deployment_manifest(output_dir / "deployment.json", "policy.pt")
    if output_dir == (run_dir / "exported").resolve():
        update_run_manifest(
            run_dir,
            stage=1,
            training_domain="simulation",
            extra={
                "policy_training": "isaac_lab_rsl_rl",
                "control_policy_origin": "trained_in_simulation",
            },
        )
    print(f"[SUCCESS] Deployment bundle: {output_dir}")
    env.close()


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
