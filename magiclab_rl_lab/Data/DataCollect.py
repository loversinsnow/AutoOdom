import argparse
import torch
import numpy as np
import os

# --- 1. 启动 Isaac Sim 应用 ---
from isaaclab.app import AppLauncher

# 解析参数
parser = argparse.ArgumentParser(description="Record Z1 Data for AutoOdom")
parser.add_argument("--task", type=str, default="Magiclab-Z1-12dof-Velocity")
parser.add_argument("--num_envs", type=int, default=1)

# [设置] 默认模型路径
parser.add_argument(
    "--checkpoint", 
    type=str, 
    default="/home/dogogod/magiclab_rl_lab/logs/rsl_rl/magiclab_z1_12dof_velocity/Z1/policy_gait1_v13_8_8600.pt", 
    help="Path to the trained policy checkpoint (.pt)"
)
parser.add_argument("--device", type=str, default="cuda:0", help="Device for execution")

# [设置] 默认 Headless 模式
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
import magiclab_rl_lab  # 导入以注册 Magiclab 环境
from rsl_rl.modules import ActorCritic

def main():
    # 1. 解析环境配置
    env_cfg = parse_env_cfg(args_cli.task, device=args_cli.device, num_envs=args_cli.num_envs)
    
    # --- [关键要求] 强制关闭噪声 ---
    # 确保收集的数据是纯净的仿真真值 (Ground Truth)
    if hasattr(env_cfg, "observations") and hasattr(env_cfg.observations, "policy"):
        env_cfg.observations.policy.enable_corruption = False
        print("[INFO] Noise disabled (enable_corruption=False) for data collection.")
    
    # 2. 创建环境
    env = ManagerBasedRLEnv(cfg=env_cfg)

    # 3. 加载模型
    print(f"[INFO] Loading checkpoint from: {args_cli.checkpoint}")
    if not os.path.exists(args_cli.checkpoint):
        raise FileNotFoundError(f"Checkpoint file not found: {args_cli.checkpoint}")
        
    loaded_model = torch.load(args_cli.checkpoint, map_location="cpu", weights_only=False)
    
    obs, _ = env.reset()
    
    # 检查加载的是 TorchScript 模型还是普通 checkpoint
    if isinstance(loaded_model, torch.jit.ScriptModule):
        # TorchScript 模型
        print("[INFO] Loaded TorchScript model directly.")
        policy_model = loaded_model.to(env.device)
        policy_model.eval()
        use_torchscript = True
    else:
        # 普通 Checkpoint 模型
        obs_groups = {"policy": ["policy"]}
        if "critic" in env.observation_manager.group_obs_dim:
            obs_groups["critic"] = ["critic"]
        else:
            obs_groups["critic"] = ["policy"]

        num_actions = env.action_space.shape[1]
        hidden_dims = [512, 256, 128] # 根据 Z1 的训练配置可能需要调整，通常是这个

        policy_model = ActorCritic(
            obs, obs_groups, num_actions,
            actor_hidden_dims=hidden_dims,
            critic_hidden_dims=hidden_dims,
            **loaded_model.get("model_kwargs", {})
        )
        
        policy_model.load_state_dict(loaded_model["model_state_dict"])
        policy_model.to(env.device)
        policy_model.eval()
        use_torchscript = False

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
    # 记录初始位置，作为差分基准
    last_root_pos = robot.data.root_pos_w.clone()

    print(f"[INFO] Starting recording for {args_cli.steps} valid steps (Headless: {args_cli.headless})...")
    
    collected_steps = 0
    
    with torch.inference_mode():
        while collected_steps < args_cli.steps:
            # --- 策略推理 ---
            if use_torchscript:
                if isinstance(obs, dict):
                    obs_tensor = obs["policy"]
                else:
                    obs_tensor = obs
                actions = policy_model(obs_tensor)
            else:
                try:
                    actions = policy_model.act(obs)
                except:
                    actions = policy_model.act(obs["policy"])
            
            # --- 环境步进 ---
            step_result = env.step(actions)
            if len(step_result) == 5:
                obs, rewards, terminated, truncated, extras = step_result
                dones = terminated | truncated
            else:
                obs, rewards, dones, extras = step_result

            # =========================================================
            # [核心逻辑] 瞬移帧/重置帧过滤
            # =========================================================
            current_root_pos = robot.data.root_pos_w
            
            # 1. 物理距离判定: 如果一步移动超过 0.5m，绝对是瞬移 (0.5m / 0.02s = 25m/s)
            move_dist = torch.norm(current_root_pos - last_root_pos, dim=-1)
            is_physics_reset = torch.any(move_dist > 0.5)
            
            # 2. 环境信号判定: Dones 信号
            is_env_reset = torch.any(dones)
            
            # 综合判定
            if is_env_reset or is_physics_reset:
                # 这是一个无效帧（发生了重置或瞬移）
                
                # 关键步骤：更新 last_root_pos 为当前的新起点
                # 这样下一次循环时，delt_pos = next_pos - current_pos (新起点)，就是正确的微小增量
                last_root_pos = current_root_pos.clone()
                
                # 如果是 RNN/LSTM 策略，需要重置内部状态
                if hasattr(policy_model, "reset"):
                    if use_torchscript:
                        # TorchScript 模型的 reset 通常不带参数或自动处理
                        try: 
                            policy_model.reset()
                        except: 
                            pass # 有些导出模型可能没有 reset 方法，或者是无状态的
                    else:
                        # RSL-RL ActorCritic 需要重置索引
                        policy_model.reset(dones.nonzero(as_tuple=False).flatten())
                
                # 跳过本次保存，不增加 collected_steps 计数
                continue
            
            # =========================================================
            # [有效数据保存] 只有未发生重置的帧才会运行到这里
            # =========================================================
            
            # 1. 计算世界系位移
            delta_pos_world = (current_root_pos - last_root_pos).unsqueeze(-1)
            
            # 2. 投影到局部系 (Body Frame)
            rot_mat_tensor = matrix_from_quat(robot.data.root_quat_w)
            delta_pos_local = torch.bmm(rot_mat_tensor.transpose(1, 2), delta_pos_world).squeeze(-1)

            # 3. 存入列表
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
            
            # 更新计数器
            collected_steps += 1
            if collected_steps % 100 == 0:
                print(f"Collected {collected_steps}/{args_cli.steps} valid frames...", end="\r")
            
            # 更新上一帧位置
            last_root_pos = current_root_pos.clone()

    # 5. 保存数据 (按自然数顺序命名)
    data_dir = os.path.dirname(os.path.abspath(__file__))  # 保存到脚本所在目录
    base_filename = "Z1"
    counter = 0
    
    # 查找下一个可用的文件名 Z1-0.npz, Z1-1.npz ...
    while True:
        save_path = os.path.join(data_dir, f"{base_filename}-{counter}.npz")
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