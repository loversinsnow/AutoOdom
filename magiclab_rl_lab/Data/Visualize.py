#!/usr/bin/env python3
"""
AutoOdom Stage 1: 推理与评估脚本
================================

用于:
- 加载训练好的 Stage 1 模型
- 在测试数据上进行推理
- 评估模型性能
- 可视化预测结果
"""

import os
import glob
import argparse
import random
import numpy as np
import torch
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

# 从训练脚本导入模型和数据集类
from Train import AutoOdomMLP, AutoOdomLSTM, AutoOdomTransformer, AutoOdomDataset


class Stage1Evaluator:
    """Stage 1 模型评估器"""
    
    def __init__(self, model_path, data_dir, device='cuda:0', model_type='mlp'):
        """
        Args:
            model_path: 模型权重路径
            data_dir: 数据目录
            device: 计算设备
            model_type: 模型类型
        """
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        self.data_dir = data_dir
        self.model_type = model_type
        
        # 加载标准化参数
        stats_path = os.path.join(os.path.dirname(model_path), 'normalization_stats.npz')
        if os.path.exists(stats_path):
            self.stats = dict(np.load(stats_path))
            print(f"[Info] 加载标准化参数: {stats_path}")
        else:
            print("[Warning] 未找到标准化参数文件，使用默认值")
            self.stats = None
        
        # 加载模型
        self.model = self._load_model(model_path)
        print(f"[Info] 模型加载完成，设备: {self.device}")
    
    def _load_model(self, model_path):
        """加载模型"""
        checkpoint = torch.load(model_path, map_location=self.device)
        
        # 推断输入维度
        state_dict = checkpoint['model_state_dict']
        first_layer_key = [k for k in state_dict.keys() if 'weight' in k][0]
        input_dim = state_dict[first_layer_key].shape[1]
        
        print(f"[Info] 推断输入维度: {input_dim}")
        
        # 创建模型
        if self.model_type == 'mlp':
            model = AutoOdomMLP(input_dim=input_dim, hidden_dims=[256, 128, 64], output_dim=2)
        elif self.model_type == 'lstm':
            model = AutoOdomLSTM(input_dim=input_dim, hidden_dim=256, num_layers=2, output_dim=2)
        else:
            model = AutoOdomTransformer(input_dim=input_dim, d_model=256, output_dim=2)
        
        model.load_state_dict(checkpoint['model_state_dict'])
        model.to(self.device)
        model.eval()
        
        print(f"[Info] 模型来自 epoch {checkpoint.get('epoch', 'unknown')}")
        print(f"[Info] 验证损失: {checkpoint.get('val_loss', 'unknown')}")
        
        return model
    
    def evaluate_file(self, npz_path):
        """
        评估单个 npz 文件
        
        Returns:
            predictions: 预测的位移增量 (N, 2) [dx, dy]
            targets: 真实位移增量 (N, 2) [dx, dy]
            trajectory_pred: 积分后的预测轨迹 (N, 2)
            trajectory_gt: 积分后的真实轨迹 (N, 2)
        """
        data = np.load(npz_path)
        
        # 加载所有特征 (按论文顺序: A_t, v_cmd, ω, q, q_dot, R, Δp)
        joint_commands = data['joint_commands'].astype(np.float32)  # A_t
        cmd_vel = data['cmd_vel'].astype(np.float32)                # v_cmd
        gyro_ang_vel = data['gyro_ang_vel'].astype(np.float32)      # ω
        joint_pos = data['joint_pos'].astype(np.float32)            # q
        joint_vel = data['joint_vel'].astype(np.float32)            # q_dot
        base_rot_mat = data['base_rot_mat'].astype(np.float32)      # R
        pos_increment = data['pos_increment_hist'].astype(np.float32)  # Δp (GT)
        
        N = len(joint_pos)
        
        # 标准化 (按论文顺序)
        if self.stats is not None:
            joint_commands_norm = (joint_commands - self.stats['joint_commands_mean']) / self.stats['joint_commands_std']
            cmd_vel_norm = (cmd_vel - self.stats['cmd_vel_mean']) / self.stats['cmd_vel_std']
            gyro_norm = (gyro_ang_vel - self.stats['gyro_ang_vel_mean']) / self.stats['gyro_ang_vel_std']
            joint_pos_norm = (joint_pos - self.stats['joint_pos_mean']) / self.stats['joint_pos_std']
            joint_vel_norm = (joint_vel - self.stats['joint_vel_mean']) / self.stats['joint_vel_std']
        else:
            joint_commands_norm = joint_commands
            cmd_vel_norm = cmd_vel
            gyro_norm = gyro_ang_vel
            joint_pos_norm = joint_pos
            joint_vel_norm = joint_vel
        
        # 构建特征 (按论文顺序)
        rot_features = base_rot_mat[:, :2, :].reshape(N, -1)  # R: 前两行展平 (6维)
        pos_inc_hist = pos_increment[:, :2]  # Δp: 历史位移 (2维, Stage1用GT)
        
        features = np.concatenate([
            joint_commands_norm,  # 12 - A_t
            cmd_vel_norm,         # 3  - v_cmd
            gyro_norm,            # 3  - ω
            joint_pos_norm,       # 12 - q
            joint_vel_norm,       # 12 - q_dot
            rot_features,         # 6  - R
            pos_inc_hist,         # 2  - Δp
        ], axis=1)
        
        # 推理
        features_tensor = torch.from_numpy(features).to(self.device)
        
        with torch.no_grad():
            predictions = self.model(features_tensor).cpu().numpy()
        
        # 只取 x, y 两维
        targets = pos_increment[:, :2]
        
        # 积分得到轨迹 (2D)
        trajectory_pred = np.cumsum(predictions, axis=0)
        trajectory_gt = np.cumsum(targets, axis=0)
        
        return predictions, targets, trajectory_pred, trajectory_gt
    
    def compute_metrics(self, predictions, targets):
        """计算评估指标"""
        # MAE
        mae = np.mean(np.abs(predictions - targets), axis=0)
        
        # RMSE
        rmse = np.sqrt(np.mean((predictions - targets) ** 2, axis=0))
        
        # 相对误差
        rel_error = np.mean(np.abs(predictions - targets) / (np.abs(targets) + 1e-8), axis=0)
        
        return {
            'mae': mae,
            'rmse': rmse,
            'rel_error': rel_error,
            'mae_total': np.mean(mae),
            'rmse_total': np.mean(rmse)
        }
    
    def evaluate_all(self, file_pattern="Z1-*.npz", max_files=10):
        """评估多个文件（随机选取）"""
        all_files = glob.glob(os.path.join(self.data_dir, file_pattern))
        if len(all_files) > max_files:
            file_list = random.sample(all_files, max_files)
        else:
            file_list = all_files
        
        all_predictions = []
        all_targets = []
        
        print(f"\n评估 {len(file_list)} 个文件...")
        
        for fpath in file_list:
            preds, targets, _, _ = self.evaluate_file(fpath)
            all_predictions.append(preds)
            all_targets.append(targets)
        
        all_predictions = np.concatenate(all_predictions, axis=0)
        all_targets = np.concatenate(all_targets, axis=0)
        
        metrics = self.compute_metrics(all_predictions, all_targets)
        
        print("\n" + "=" * 50)
        print("Stage 1 评估结果 (2D: x, y)")
        print("=" * 50)
        print(f"总样本数: {len(all_predictions)}")
        print(f"MAE: x={metrics['mae'][0]:.6f}, y={metrics['mae'][1]:.6f}")
        print(f"RMSE: x={metrics['rmse'][0]:.6f}, y={metrics['rmse'][1]:.6f}")
        print(f"相对误差: x={metrics['rel_error'][0]:.2%}, y={metrics['rel_error'][1]:.2%}")
        print(f"平均 MAE: {metrics['mae_total']:.6f}")
        print(f"平均 RMSE: {metrics['rmse_total']:.6f}")
        print("=" * 50)
        
        return metrics


def visualize_trajectory(evaluator, npz_path, save_path=None):
    """可视化单个文件的轨迹预测结果 (2D: x, y)"""
    predictions, targets, traj_pred, traj_gt = evaluator.evaluate_file(npz_path)
    
    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(2, 3, figure=fig)
    
    # 1. XY 平面轨迹对比
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(traj_gt[:, 0], traj_gt[:, 1], 'b-', linewidth=1.5, label='Ground Truth')
    ax1.plot(traj_pred[:, 0], traj_pred[:, 1], 'r--', linewidth=1.5, label='Prediction')
    ax1.set_xlabel('X (m)')
    ax1.set_ylabel('Y (m)')
    ax1.set_title('XY Trajectory')
    ax1.legend()
    ax1.axis('equal')
    ax1.grid(True, alpha=0.3)
    
    # 2. X 位移随时间变化
    time_steps = np.arange(len(targets))
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(time_steps, traj_gt[:, 0], 'b-', linewidth=1, label='GT')
    ax2.plot(time_steps, traj_pred[:, 0], 'r--', linewidth=1, label='Pred')
    ax2.set_xlabel('Time Step')
    ax2.set_ylabel('X Position (m)')
    ax2.set_title('X Position Over Time')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. Y 位移随时间变化
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.plot(time_steps, traj_gt[:, 1], 'b-', linewidth=1, label='GT')
    ax3.plot(time_steps, traj_pred[:, 1], 'r--', linewidth=1, label='Pred')
    ax3.set_xlabel('Time Step')
    ax3.set_ylabel('Y Position (m)')
    ax3.set_title('Y Position Over Time')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4-5. 各维度位移增量时序对比
    labels = ['dx', 'dy']
    
    for i, label in enumerate(labels):
        ax = fig.add_subplot(gs[1, i])
        ax.plot(time_steps, targets[:, i], 'b-', linewidth=0.8, alpha=0.7, label='Ground Truth')
        ax.plot(time_steps, predictions[:, i], 'r-', linewidth=0.8, alpha=0.7, label='Prediction')
        ax.set_xlabel('Time Step')
        ax.set_ylabel(f'{label} (m)')
        ax.set_title(f'{label} Increment Over Time')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    # 6. 误差分布直方图
    ax6 = fig.add_subplot(gs[1, 2])
    error_x = predictions[:, 0] - targets[:, 0]
    error_y = predictions[:, 1] - targets[:, 1]
    ax6.hist(error_x, bins=50, alpha=0.6, color='blue', edgecolor='white', label='dx error')
    ax6.hist(error_y, bins=50, alpha=0.6, color='orange', edgecolor='white', label='dy error')
    ax6.axvline(x=0, color='red', linestyle='--', linewidth=1)
    ax6.set_xlabel('Error (m)')
    ax6.set_ylabel('Count')
    ax6.set_title(f'Error Distribution\n(μ_x={np.mean(error_x):.4f}, μ_y={np.mean(error_y):.4f})')
    ax6.legend()
    ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"[Info] 图片已保存: {save_path}")
    
    plt.show()


def visualize_multiple_trajectories(evaluator, data_dir, num_files=5, save_path=None):
    """可视化多个轨迹的 XY 平面对比（随机选取）"""
    all_files = glob.glob(os.path.join(data_dir, "Z1-*.npz"))
    if len(all_files) > num_files:
        file_list = random.sample(all_files, num_files)
    else:
        file_list = all_files
    
    fig, axes = plt.subplots(1, num_files, figsize=(4 * num_files, 4))
    if num_files == 1:
        axes = [axes]
    
    for idx, (ax, fpath) in enumerate(zip(axes, file_list)):
        _, _, traj_pred, traj_gt = evaluator.evaluate_file(fpath)
        
        ax.plot(traj_gt[:, 0], traj_gt[:, 1], 'b-', linewidth=1.5, label='GT')
        ax.plot(traj_pred[:, 0], traj_pred[:, 1], 'r--', linewidth=1.5, label='Pred')
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.set_title(f'File {idx}')
        ax.legend(fontsize=8)
        ax.axis('equal')
        ax.grid(True, alpha=0.3)
    
    plt.suptitle('Stage 1 Trajectory Predictions (XY Plane)', fontsize=14)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"[Info] 图片已保存: {save_path}")
    
    plt.show()


def main():
    parser = argparse.ArgumentParser(description='AutoOdom Stage 1 Inference & Evaluation')
    
    parser.add_argument('--model', type=str, required=True,
                        help='模型权重路径')
    parser.add_argument('--data_dir', type=str, 
                        default='/home/dogogod/magiclab_rl_lab/Data',
                        help='数据目录')
    parser.add_argument('--model_type', type=str, default='mlp',
                        choices=['mlp', 'lstm', 'transformer'],
                        help='模型类型')
    parser.add_argument('--device', type=str, default='cuda:0',
                        help='计算设备')
    parser.add_argument('--num_files', type=int, default=5,
                        help='可视化文件数量')
    parser.add_argument('--eval_files', type=int, default=50,
                        help='评估文件数量')
    parser.add_argument('--visualize', action='store_true',
                        help='是否生成可视化图表')
    parser.add_argument('--save_vis', type=str, default=None,
                        help='可视化图片保存路径')
    
    args = parser.parse_args()
    
    # 创建评估器
    evaluator = Stage1Evaluator(
        model_path=args.model,
        data_dir=args.data_dir,
        device=args.device,
        model_type=args.model_type
    )
    
    # 评估
    metrics = evaluator.evaluate_all(max_files=args.eval_files)
    
    # 可视化
    if args.visualize:
        # 单文件详细可视化（随机选取）
        all_files = glob.glob(os.path.join(args.data_dir, "Z1-*.npz"))
        test_file = random.choice(all_files)
        print(f"\n可视化文件: {os.path.basename(test_file)}")
        save_path = args.save_vis or os.path.join(args.data_dir, 'stage1_visualization.png')
        visualize_trajectory(evaluator, test_file, save_path=save_path)
        
        # 多轨迹对比
        multi_save_path = save_path.replace('.png', '_multi.png')
        visualize_multiple_trajectories(evaluator, args.data_dir, 
                                        num_files=args.num_files, 
                                        save_path=multi_save_path)


if __name__ == '__main__':
    main()
