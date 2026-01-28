import argparse
import torch
import numpy as np
import os
import matplotlib.pyplot as plt  # [新增] 恢复绘图库

# --- 1. 启动 Isaac Sim 应用 ---
from isaaclab.app import AppLauncher

# 解析参数
parser = argparse.ArgumentParser(description="Record Z1 Data for AutoOdom (With Plotting)")
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
import magiclab_rl_lab 
from rsl_rl.modules import ActorCritic

def plot_trajectory_verification(file_path):
    """
    [新增] 绘图验证函数
    读取保存的 .npz 文件，重构轨迹并绘制对比图。
    如果检测到位置突变（因为过滤了瞬移帧，真值会不连续），则断开连线。
    """
    print(f"[INFO] Plotting trajectory verification from {file_path}...")
    
    data = np.load(file_path)
    
    # 辅助函数：处理多环境维度
    def get_env0(arr):
        if arr.ndim > 1 and args_cli.num_envs > 1:
            return arr[:, 0]
        return arr

    gt_pos_world = get_env0(data["root_pos_abs"])      
    local_inc = get_env0(data["pos_increment_hist"])   
    rot_mats = get_env0(data["base_rot_mat"])          

    # --- 准备绘图数据 (插入 NaN 以断开不连续的轨迹) ---
    plot_gt_x, plot_gt_y = [], []
    plot_recon_x, plot_recon_y = [], []
    
    # 初始化
    current_recon_pos = gt_pos_world[0].copy()
    
    # 加入起点
    plot_gt_x.append(gt_pos_world[0, 0])
    plot_gt_y.append(gt_pos_world[0, 1])
    plot_recon_x.append(current_recon_pos[0])
    plot_recon_y.append(current_recon_pos[1])
    
    for t in range(1, len(gt_pos_world)):
        # 1. 计算真值在世界系下的距离
        dist = np.linalg.norm(gt_pos_world[t] - gt_pos_world[t-1])
        
        # 2. 如果两帧之间真值距离超过 0.5m，说明这是两条独立的轨迹（中间发生了重置）
        if dist > 0.5:
            # 插入 NaN 使 Matplotlib 断开连线
            plot_gt_x.append(np.nan)
            plot_gt_y.append(np.nan)
            plot_recon_x.append(np.nan)
            plot_recon_y.append(np.nan)
            
            # 重构轨迹必须对齐到新的真值起点，否则会飞出去
            current_recon_pos = gt_pos_world[t].copy()
            
            # 存入新起点的坐标
            plot_gt_x.append(gt_pos_world[t, 0])
            plot_gt_y.append(gt_pos_world[t, 1])
            plot_recon_x.append(current_recon_pos[0])
            plot_recon_y.append(current_recon_pos[1])
            continue
        
        # 3. 正常的积分逻辑 (Dead Reckoning)
        # P_new = P_old + R * delta_local
        R = rot_mats[t-1] 
        dp_local = local_inc[t] 
        dp_world = R @ dp_local
        current_recon_pos += dp_world
        
        plot_gt_x.append(gt_pos_world[t, 0])
        plot_gt_y.append(gt_pos_world[t, 1])
        plot_recon_x.append(current_recon_pos[0])
        plot_recon_y.append(current_recon_pos[1])

    # --- 绘图 ---
    plt.figure(figsize=(12, 10))
    
    # 绘制 Ground Truth
    plt.plot(plot_gt_x, plot_gt_y, label='Ground Truth (Abs)', 
             color='blue', linewidth=3, alpha=0.4)
    
    # 绘制 Reconstructed
    plt.plot(plot_recon_x, plot_recon_y, label='Reconstructed (Integrated)', 
             color='red', linestyle='--', linewidth=1.5)
    
    # 标记起点
    plt.scatter(plot_gt_x[0], plot_gt_y[0], c='green', s=120, label='Start', marker='^', zorder=5)
    
    plt.title(f"Trajectory Verification: {os.path.basename(file_path)}\n(Segments should align perfectly)")
    plt.xlabel("Position X (m)")
    plt.ylabel("Position Y (m)")
    plt.legend()
    plt.grid(True)
    plt.axis('equal')
    
    # 保存图片
    image_path = file_path.replace(".npz", "_verify.png")
    plt.savefig(image_path, dpi=150)
    print(f"[SUCCESS] Verification plot saved to {os.path.abspath(image_path)}")
    plt.close() # 关闭画布释放内存

def main():
    # 1. 解析环境配置
    env_cfg = parse_env_cfg(args_cli.task, device=args_cli.device, num_envs=args_cli.num_envs)
    
    # --- 强制关闭噪声 ---
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
    
    # 模型加载逻辑
    if isinstance(loaded_model, torch.jit.ScriptModule):
        print("[INFO] Loaded TorchScript model directly.")
        policy_model = loaded_model.to(env.device)
        policy_model.eval()
        use_torchscript = True
    else:
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
    last_root_pos = robot.data.root_pos_w.clone()

    print(f"[INFO] Starting recording for {args_cli.steps} valid steps (Headless: {args_cli.headless})...")
    
    collected_steps = 0
    
    with torch.inference_mode():
        while collected_steps < args_cli.steps:
            # 推理
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
            
            # 步进
            step_result = env.step(actions)
            if len(step_result) == 5:
                obs, rewards, terminated, truncated, extras = step_result
                dones = terminated | truncated
            else:
                obs, rewards, dones, extras = step_result

            # --- 过滤逻辑 ---
            current_root_pos = robot.data.root_pos_w
            
            # 物理位移判定 (>0.5m)
            move_dist = torch.norm(current_root_pos - last_root_pos, dim=-1)
            is_invalid = torch.any(dones) or torch.any(move_dist > 0.5)

            if is_invalid:
                last_root_pos = current_root_pos.clone()
                if hasattr(policy_model, "reset"):
                    if use_torchscript:
                        try: policy_model.reset()
                        except: pass
                    else:
                        policy_model.reset(dones.nonzero(as_tuple=False).flatten())
                continue
            
            # --- 保存有效数据 ---
            delta_pos_world = (current_root_pos - last_root_pos).unsqueeze(-1)
            rot_mat_tensor = matrix_from_quat(robot.data.root_quat_w)
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

    # 5. 保存数据
    data_dir = os.path.dirname(os.path.abspath(__file__))
    base_filename = "Z1"
    counter = 0
    
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
    
    # 6. 调用绘图函数
    plot_trajectory_verification(save_path)

if __name__ == "__main__":
    main()