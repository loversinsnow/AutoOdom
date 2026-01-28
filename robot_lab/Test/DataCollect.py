import argparse
import torch
import numpy as np
import os

# --- 1. 启动 Isaac Sim 应用 ---
from isaaclab.app import AppLauncher

# 解析参数
parser = argparse.ArgumentParser(description="Record Booster T1 Data for AutoOdom")
parser.add_argument("--task", type=str, default="RobotLab-Isaac-Velocity-Flat-Booster-T1-v0")
parser.add_argument("--num_envs", type=int, default=1)

# [修改] 设置了默认模型路径
parser.add_argument(
    "--checkpoint", 
    type=str, 
    default="/home/dogogod/robot_lab/logs/rsl_rl/booster_t1_flat/2026-01-23_23-22-57/model_14999.pt", 
    help="Path to the trained policy checkpoint (.pt)"
)
parser.add_argument("--device", type=str, default="cuda:0", help="Device for execution")

# [修改] 默认开启 Headless (default=True)，这样不加参数也会后台运行
# 注意：这会导致无论是否加 --headless 都是 True。如果想开 GUI，需要改代码或去掉 default=True
parser.add_argument("--headless", action="store_true", default=True, help="Force display off at all times.")

parser.add_argument("--steps", type=int, default=1000, help="Number of valid steps to record")
args_cli = parser.parse_args()

# 初始化 AppLauncher
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

# --- 2. 导入其余模块 ---
import isaaclab.sim as sim_utils
from isaaclab.envs import ManagerBasedRLEnv 
from isaaclab_tasks.utils import get_checkpoint_path, parse_env_cfg
from isaaclab.utils.math import matrix_from_quat
import robot_lab 
from rsl_rl.modules import ActorCritic

def main():
    # 1. 解析环境配置
    env_cfg = parse_env_cfg(args_cli.task, device=args_cli.device, num_envs=args_cli.num_envs)
    
    # --- [关键要求] 强制关闭噪声 ---
    if hasattr(env_cfg, "observations") and hasattr(env_cfg.observations, "policy"):
        env_cfg.observations.policy.enable_corruption = False
        print("[INFO] Noise disabled (enable_corruption=False) for data collection.")
    
    # 2. 创建环境
    env = ManagerBasedRLEnv(cfg=env_cfg)

    # 3. 加载模型
    print(f"[INFO] Loading checkpoint from: {args_cli.checkpoint}")
    if not os.path.exists(args_cli.checkpoint):
        raise FileNotFoundError(f"Checkpoint file not found: {args_cli.checkpoint}")
        
    loaded_dict = torch.load(args_cli.checkpoint, map_location="cpu")
    
    obs, _ = env.reset()
    
    # 处理 Observation Groups
    obs_groups = {"policy": ["policy"]}
    if "critic" in env.observation_manager.group_obs_dim:
        obs_groups["critic"] = ["critic"]
    else:
        obs_groups["critic"] = ["policy"]

    num_actions = env.action_space.shape[1]
    hidden_dims = [512, 256, 128]

    policy_model = ActorCritic(
        obs, obs_groups, num_actions,
        actor_hidden_dims=hidden_dims,
        critic_hidden_dims=hidden_dims,
        **loaded_dict.get("model_kwargs", {})
    )
    
    policy_model.load_state_dict(loaded_dict["model_state_dict"])
    policy_model.to(env.device)
    policy_model.eval()

    # 4. 初始化数据容器
    data_log = {
        "joint_commands": [],     
        "cmd_vel": [],            
        "gyro_ang_vel": [],       
        "joint_pos": [],          
        "joint_vel": [],          
        "base_rot_mat": [],       
        "pos_increment_hist": [], 
        "root_pos_abs": []        
    }

    robot = env.scene["robot"]
    last_root_pos = robot.data.root_pos_w.clone()

    print(f"[INFO] Starting recording for {args_cli.steps} valid steps (Headless: {args_cli.headless})...")
    
    collected_steps = 0
    
    with torch.inference_mode():
        while collected_steps < args_cli.steps:
            # 策略推理
            try:
                actions = policy_model.act(obs)
            except:
                actions = policy_model.act(obs["policy"])
            
            # 环境步进
            step_result = env.step(actions)
            if len(step_result) == 5:
                obs, rewards, terminated, truncated, extras = step_result
                dones = terminated | truncated
            else:
                obs, rewards, dones, extras = step_result

            # --- 数据过滤逻辑 ---
            current_root_pos = robot.data.root_pos_w
            
            # 物理距离判断瞬移 (阈值 0.5m)
            move_dist = torch.norm(current_root_pos - last_root_pos, dim=-1)
            is_invalid_step = torch.any(dones) or torch.any(move_dist > 0.5)

            if is_invalid_step:
                last_root_pos = current_root_pos.clone()
                if hasattr(policy_model, "reset"):
                    policy_model.reset(dones.nonzero(as_tuple=False).flatten())
                continue
            
            # --- 有效帧保存逻辑 ---
            delta_pos_world = (current_root_pos - last_root_pos).unsqueeze(-1)
            rot_mat_tensor = matrix_from_quat(robot.data.root_quat_w)
            # 投影到局部系
            delta_pos_local = torch.bmm(rot_mat_tensor.transpose(1, 2), delta_pos_world).squeeze(-1)

            data_log["joint_commands"].append(actions.cpu().numpy())
            
            if "base_velocity" in env.command_manager.active_terms:
                cmd = env.command_manager.get_command("base_velocity")
            else:
                cmd_term = list(env.command_manager.active_terms.keys())[0]
                cmd = env.command_manager.get_command(cmd_term)
            data_log["cmd_vel"].append(cmd.cpu().numpy())

            data_log["joint_pos"].append(robot.data.joint_pos.cpu().numpy())
            data_log["joint_vel"].append(robot.data.joint_vel.cpu().numpy())
            data_log["gyro_ang_vel"].append(robot.data.root_ang_vel_b.cpu().numpy())
            data_log["base_rot_mat"].append(rot_mat_tensor.cpu().numpy())
            
            data_log["pos_increment_hist"].append(delta_pos_local.cpu().numpy())
            data_log["root_pos_abs"].append(current_root_pos.cpu().numpy())
            
            collected_steps += 1
            if collected_steps % 100 == 0:
                print(f"Collected {collected_steps}/{args_cli.steps} valid frames...", end="\r")
            
            last_root_pos = current_root_pos.clone()

    # 5. 保存数据 (按自然数顺序命名)
    base_filename = "booster_t1_stage1_data"
    counter = 0
    
    while True:
        save_path = f"{base_filename}_{counter}.npz"
        if not os.path.exists(save_path):
            break
        counter += 1
    
    final_data = {}
    for k, v in data_log.items():
        arr = np.array(v)
        if args_cli.num_envs == 1 and arr.ndim > 1:
            arr = arr.squeeze(1)
        final_data[k] = arr

    np.savez(save_path, **final_data)
    print(f"\n[SUCCESS] Data saved to {os.path.abspath(save_path)}")

    env.close()

if __name__ == "__main__":
    main()