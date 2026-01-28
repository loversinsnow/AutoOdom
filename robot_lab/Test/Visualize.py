"""
AutoOdom 训练效果可视化验证程序

随机选取5个数据文件，对比模型预测与真实轨迹
"""

import argparse
import os
import glob
import random
import numpy as np
import torch
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

# 导入训练模块
from Train import AutoOdomNet, AutoOdomDataset


def load_model(checkpoint_path, input_dim, hidden_dim=128, num_layers=3, device='cuda'):
    """加载训练好的模型"""
    model = AutoOdomNet(
        input_dim=input_dim,
        hidden_dim=hidden_dim,
        num_layers=num_layers,
        output_dim=3,
        dropout=0.0  # 推理时关闭dropout
    )
    
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.to(device)
    model.eval()
    
    # 加载归一化参数
    feature_mean = checkpoint.get('feature_mean', None)
    feature_std = checkpoint.get('feature_std', None)
    
    if feature_mean is not None:
        feature_mean = feature_mean.to(device)
        feature_std = feature_std.to(device)
    
    print(f"[INFO] Loaded model from {checkpoint_path}")
    print(f"[INFO] Best val loss: {checkpoint.get('best_val_loss', 'N/A')}")
    
    return model, feature_mean, feature_std


def prepare_sequence_data(data_file, history_len=50):
    """从单个数据文件准备序列数据"""
    data = np.load(data_file)
    
    # 提取特征
    rot_mat = data['base_rot_mat'].astype(np.float32)
    gravity_vec = rot_mat[:, :, 2]  # 重力向量
    
    joint_pos = data['joint_pos'].astype(np.float32)
    joint_vel = data['joint_vel'].astype(np.float32)
    gyro_ang_vel = data['gyro_ang_vel'].astype(np.float32)
    joint_commands = data['joint_commands'].astype(np.float32)
    pos_increment = data['pos_increment_hist'].astype(np.float32)
    
    T = len(joint_pos)
    
    # 构建历史窗口特征
    all_features = []
    all_targets = []
    
    for t in range(history_len - 1, T):
        # 历史窗口
        history = []
        for h in range(t - history_len + 1, t + 1):
            # Auto-regressive: previous velocity (h-1)
            if h > 0:
                prev_vel = pos_increment[h - 1]
            else:
                prev_vel = np.zeros(3, dtype=np.float32)
            
            feat = np.concatenate([
                joint_pos[h],
                joint_vel[h],
                gyro_ang_vel[h],
                gravity_vec[h],
                joint_commands[h],
                prev_vel,  # previous position increment
            ])
            history.append(feat)
        
        history = np.stack(history, axis=0)
        all_features.append(history)
        all_targets.append(pos_increment[t])
    
    features = np.stack(all_features, axis=0)
    targets = np.stack(all_targets, axis=0)
    
    return features, targets


@torch.no_grad()
def predict_trajectory(model, features, feature_mean, feature_std, device):
    """使用模型预测轨迹"""
    features_tensor = torch.from_numpy(features).to(device)
    
    if feature_mean is not None:
        features_tensor = (features_tensor - feature_mean) / feature_std
    
    # 分批处理避免显存溢出
    batch_size = 512
    predictions = []
    
    for i in range(0, len(features_tensor), batch_size):
        batch = features_tensor[i:i+batch_size]
        pred = model(batch)
        predictions.append(pred.cpu().numpy())
    
    return np.concatenate(predictions, axis=0)


def visualize_single_trajectory(ax_xy, ax_error, ax_increments, 
                                 predictions, targets, file_name, idx):
    """可视化单个轨迹"""
    # 累积得到轨迹
    pred_traj = np.cumsum(predictions, axis=0)
    gt_traj = np.cumsum(targets, axis=0)
    
    # XY轨迹对比
    ax_xy.plot(gt_traj[:, 0], gt_traj[:, 1], 'b-', linewidth=2, label='Ground Truth')
    ax_xy.plot(pred_traj[:, 0], pred_traj[:, 1], 'r--', linewidth=1.5, label='Prediction')
    ax_xy.scatter([gt_traj[0, 0]], [gt_traj[0, 1]], c='green', s=80, marker='^', zorder=5)
    ax_xy.scatter([gt_traj[-1, 0]], [gt_traj[-1, 1]], c='black', s=80, marker='x', zorder=5)
    ax_xy.set_xlabel('X (m)')
    ax_xy.set_ylabel('Y (m)')
    ax_xy.set_title(f'File {idx+1}: {file_name}')
    ax_xy.legend(loc='best', fontsize=8)
    ax_xy.grid(True, alpha=0.3)
    ax_xy.axis('equal')
    
    # 轨迹误差
    traj_error = np.sqrt(np.sum((pred_traj - gt_traj) ** 2, axis=1))
    t = np.arange(len(traj_error))
    ax_error.plot(t, traj_error, 'purple', linewidth=1.5)
    ax_error.fill_between(t, 0, traj_error, alpha=0.3, color='purple')
    ax_error.set_xlabel('Time Step')
    ax_error.set_ylabel('Position Error (m)')
    ax_error.set_title(f'Cumulative Error (Final: {traj_error[-1]:.3f}m)')
    ax_error.grid(True, alpha=0.3)
    
    # 位置增量对比 (X和Y)
    ax_increments.plot(t, targets[:, 0], 'b-', linewidth=1, alpha=0.7, label='GT X')
    ax_increments.plot(t, predictions[:, 0], 'r--', linewidth=1, alpha=0.7, label='Pred X')
    ax_increments.plot(t, targets[:, 1], 'c-', linewidth=1, alpha=0.7, label='GT Y')
    ax_increments.plot(t, predictions[:, 1], 'm--', linewidth=1, alpha=0.7, label='Pred Y')
    ax_increments.set_xlabel('Time Step')
    ax_increments.set_ylabel('Position Increment (m)')
    ax_increments.set_title('Position Increments Comparison')
    ax_increments.legend(loc='best', fontsize=7, ncol=2)
    ax_increments.grid(True, alpha=0.3)
    
    return traj_error[-1]


def compute_metrics(predictions, targets):
    """计算评估指标"""
    # 预测误差
    mse = np.mean((predictions - targets) ** 2)
    mae = np.mean(np.abs(predictions - targets))
    rmse = np.sqrt(mse)
    
    # 轨迹误差
    pred_traj = np.cumsum(predictions, axis=0)
    gt_traj = np.cumsum(targets, axis=0)
    traj_error = np.sqrt(np.sum((pred_traj - gt_traj) ** 2, axis=1))
    
    ate = np.mean(traj_error)
    final_error = traj_error[-1]
    
    # 相对轨迹长度
    gt_length = np.sum(np.sqrt(np.sum(targets ** 2, axis=1)))
    relative_error = final_error / max(gt_length, 1e-6) * 100
    
    return {
        'mse': mse,
        'mae': mae,
        'rmse': rmse,
        'ate': ate,
        'final_error': final_error,
        'gt_length': gt_length,
        'relative_error': relative_error
    }


def main():
    parser = argparse.ArgumentParser(description="AutoOdom Visualization")
    parser.add_argument('--data_dir', type=str, 
                        default='/home/dogogod/robot_lab/Test',
                        help='数据目录路径')
    parser.add_argument('--checkpoint', type=str, 
                        default='/home/dogogod/robot_lab/Test/auto_odom_stage1_best.pth',
                        help='模型checkpoint路径')
    parser.add_argument('--num_files', type=int, default=5,
                        help='随机选择的文件数量')
    parser.add_argument('--history_len', type=int, default=50,
                        help='历史窗口长度')
    parser.add_argument('--hidden_dim', type=int, default=128,
                        help='模型隐藏层维度')
    parser.add_argument('--num_layers', type=int, default=3,
                        help='GRU层数')
    parser.add_argument('--device', type=str, default='cuda',
                        help='设备')
    parser.add_argument('--output', type=str, 
                        default='/home/dogogod/robot_lab/Test/visualization_results.png',
                        help='输出图片路径')
    parser.add_argument('--seed', type=int, default=None,
                        help='随机种子 (不设置则每次随机)')
    
    args = parser.parse_args()
    
    # 设置随机种子
    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)
    
    device = torch.device(args.device if torch.cuda.is_available() else 'cpu')
    print(f"[INFO] Using device: {device}")
    
    # 获取数据文件列表
    data_files = sorted(glob.glob(os.path.join(args.data_dir, "booster_t1_stage1_data_*.npz")))
    print(f"[INFO] Found {len(data_files)} data files")
    
    if len(data_files) < args.num_files:
        print(f"[WARN] Only {len(data_files)} files available, using all")
        selected_files = data_files
    else:
        selected_files = random.sample(data_files, args.num_files)
    
    print(f"[INFO] Selected {len(selected_files)} files for visualization:")
    for f in selected_files:
        print(f"  - {os.path.basename(f)}")
    
    # 计算输入维度
    input_dim = 23 + 23 + 3 + 3 + 23 + 3  # joint_pos + joint_vel + gyro + gravity + commands + prev_pos_increment
    
    # 加载模型
    model, feature_mean, feature_std = load_model(
        args.checkpoint, input_dim, args.hidden_dim, args.num_layers, device
    )
    
    # 创建图形
    fig = plt.figure(figsize=(20, 4 * len(selected_files)))
    gs = GridSpec(len(selected_files), 3, figure=fig, hspace=0.35, wspace=0.25)
    
    all_metrics = []
    
    for idx, file_path in enumerate(selected_files):
        print(f"\n[INFO] Processing {os.path.basename(file_path)}...")
        
        # 准备数据
        features, targets = prepare_sequence_data(file_path, args.history_len)
        print(f"  Samples: {len(features)}")
        
        # 预测
        predictions = predict_trajectory(model, features, feature_mean, feature_std, device)
        
        # 计算指标
        metrics = compute_metrics(predictions, targets)
        all_metrics.append(metrics)
        
        print(f"  RMSE: {metrics['rmse']:.6f}")
        print(f"  Final Error: {metrics['final_error']:.4f}m")
        print(f"  GT Length: {metrics['gt_length']:.4f}m")
        print(f"  Relative Error: {metrics['relative_error']:.2f}%")
        
        # 可视化
        ax_xy = fig.add_subplot(gs[idx, 0])
        ax_error = fig.add_subplot(gs[idx, 1])
        ax_increments = fig.add_subplot(gs[idx, 2])
        
        visualize_single_trajectory(
            ax_xy, ax_error, ax_increments,
            predictions, targets,
            os.path.basename(file_path), idx
        )
    
    # 添加总标题
    avg_final_error = np.mean([m['final_error'] for m in all_metrics])
    avg_rmse = np.mean([m['rmse'] for m in all_metrics])
    avg_relative_error = np.mean([m['relative_error'] for m in all_metrics])
    
    fig.suptitle(
        f'AutoOdom Stage 1 Visualization Results\n'
        f'Avg RMSE: {avg_rmse:.6f} | Avg Final Error: {avg_final_error:.4f}m | '
        f'Avg Relative Error: {avg_relative_error:.2f}%',
        fontsize=14, fontweight='bold', y=0.995
    )
    
    # 保存图片
    plt.savefig(args.output, dpi=150, bbox_inches='tight')
    print(f"\n[INFO] Visualization saved to {args.output}")
    
    # 打印汇总统计
    print("\n" + "="*60)
    print("Summary Statistics")
    print("="*60)
    print(f"{'File':<35} {'RMSE':<12} {'Final Err':<12} {'Rel Err':<10}")
    print("-"*60)
    for idx, (file_path, metrics) in enumerate(zip(selected_files, all_metrics)):
        print(f"{os.path.basename(file_path):<35} "
              f"{metrics['rmse']:.6f}     "
              f"{metrics['final_error']:.4f}m      "
              f"{metrics['relative_error']:.2f}%")
    print("-"*60)
    print(f"{'Average':<35} "
          f"{avg_rmse:.6f}     "
          f"{avg_final_error:.4f}m      "
          f"{avg_relative_error:.2f}%")
    print("="*60)
    
    plt.close()
    print("\n[INFO] Done!")


if __name__ == "__main__":
    main()
