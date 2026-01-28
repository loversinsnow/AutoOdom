"""
AutoOdom Training Script
基于论文 "AutoOdom: Learning Auto-regressive Proprioceptive Odometry for Legged Locomotion"

论文核心思想:
1. Stage 1: 训练一个 Velocity Estimator 从本体感知数据估计速度
2. Stage 2: 使用真实世界数据进行自回归增强 (Autoregressive Enhancement)

本脚本实现 Stage 1 的监督学习训练
"""

import argparse
import os
import glob
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
from datetime import datetime
import matplotlib.pyplot as plt
from tqdm import tqdm


# ============================================================================
# 数据集定义
# ============================================================================
class AutoOdomDataset(Dataset):
    """
    AutoOdom 数据集
    
    输入特征 (本体感知 Proprioceptive + 自回归 Auto-regressive):
    - joint_pos: 关节位置 (23,)
    - joint_vel: 关节速度 (23,)
    - gyro_ang_vel: 角速度 (3,) - IMU数据
    - gravity_vec: 重力向量 (3,)
    - joint_commands: 关节指令 (23,)
    - prev_pos_increment: 上一时刻的速度/位置增量 (3,) [自回归输入]
    
    输出 (里程计):
    - pos_increment: 位置增量/速度 (3,) - 局部坐标系
    """
    
    def __init__(self, data_files, history_len=50, use_velocity=True, transform=None,
                 feature_mean=None, feature_std=None, target_mean=None, target_std=None, compute_stats=False):
        """
        Args:
            data_files: 数据文件列表
            history_len: 历史窗口长度
            use_velocity: 是否预测速度
            transform: 数据变换
            feature_mean/std: 预计算的特征统计量
            target_mean/std: 预计算的目标统计量
            compute_stats: 是否计算统计量 (通常仅训练集为True)
        """
        self.data_files = data_files
        self.history_len = history_len
        self.use_velocity = use_velocity
        self.transform = transform
        
        # 存储所有数据
        self.all_data = []
        self.sample_indices = []  # (file_idx, start_idx) pairs
        
        print(f"[INFO] Loading {len(self.data_files)} data files...")
        valid_count = 0
        
        for file_idx, file_path in enumerate(tqdm(self.data_files, desc="Loading data")):
            try:
                data = np.load(file_path)
                # 检查必要的键
                if 'joint_pos' not in data.files or 'pos_increment_hist' not in data.files:
                    continue
                # 检查其他键是否存在，如果不存在则构造全0 (增强鲁棒性)
                # 假设 joint_vel, gyro_ang_vel, joint_commands, base_rot_mat 必须存在
            except:
                continue
            
            # --- 构建数据字典 ---
            # 预处理: 转为float32
            joint_pos = data['joint_pos'].astype(np.float32)
            joint_vel = data['joint_vel'].astype(np.float32)
            gyro = data['gyro_ang_vel'].astype(np.float32)
            cmd = data['joint_commands'].astype(np.float32)
            targets = data['pos_increment_hist'].astype(np.float32)
            
            # 提取重力向量
            if 'base_rot_mat' in data.files:
                rot_mat = data['base_rot_mat'].astype(np.float32)
                if rot_mat.ndim == 3 and rot_mat.shape[1:] == (3, 3):
                    grav = rot_mat[:, :, 2]
                else:
                    # 某些格式可能不同，回退到 safe default
                    grav = np.zeros((len(joint_pos), 3), dtype=np.float32)
                    grav[:, 2] = -1.0 # 假设 Z 轴向下 ? 通常是 Z up, Gravity down (-Z)
            else:
                grav = np.zeros((len(joint_pos), 3), dtype=np.float32)

            features = {
                'joint_pos': joint_pos,
                'joint_vel': joint_vel,
                'gyro_ang_vel': gyro,
                'gravity_vec': grav,
                'joint_commands': cmd,
                'pos_increment': targets, 
            }
            
            self.all_data.append(features)
            
            # 计算有效样本数量
            num_samples = len(joint_pos) - history_len
            if num_samples > 0:
                # 注意索引映射到 self.all_data 的正确索引 (valid_count)
                current_data_idx = valid_count 
                for i in range(num_samples):
                    self.sample_indices.append((current_data_idx, i))
            
            valid_count += 1
        
        print(f"[INFO] Valid files: {valid_count}, Total samples: {len(self.sample_indices)}")
        
        # 计算输入特征维度: joint(23)+vel(23)+gyro(3)+grav(3)+cmd(23)+prev_vel(3)
        self.input_dim = 23 + 23 + 3 + 3 + 23 + 3
        print(f"[INFO] Input feature dim per timestep: {self.input_dim}")
        
        # 统计量处理
        if compute_stats and len(self.sample_indices) > 0:
            self._compute_normalization_stats()
        else:
            self.feature_mean = feature_mean if feature_mean is not None else torch.zeros(self.input_dim)
            self.feature_std = feature_std if feature_std is not None else torch.ones(self.input_dim)
            self.target_mean = target_mean if target_mean is not None else torch.zeros(3)
            self.target_std = target_std if target_std is not None else torch.ones(3)
    
    def _compute_normalization_stats(self):
        """计算数据归一化的均值和标准差"""
        print("[INFO] Computing normalization stats from training data...")
        all_features_sample = []
        all_targets_sample = []
        
        # 采样较多数据以获得准确统计
        sample_size = min(50000, len(self.sample_indices))
        sample_indices = np.random.choice(len(self.sample_indices), sample_size, replace=False)
        
        for idx in sample_indices:
            file_idx, start_idx = self.sample_indices[idx]
            
            # 取窗口最后一个时刻的特征用于统计
            t = start_idx + self.history_len - 1
            feat = self._get_features(file_idx, t)
            target = self.all_data[file_idx]['pos_increment'][t]
            
            all_features_sample.append(feat)
            all_targets_sample.append(target)
        
        all_features_sample = np.stack(all_features_sample)
        all_targets_sample = np.stack(all_targets_sample)
        
        self.feature_mean = torch.from_numpy(all_features_sample.mean(axis=0).astype(np.float32))
        self.feature_std = torch.from_numpy(all_features_sample.std(axis=0).astype(np.float32) + 1e-8)
        self.target_mean = torch.from_numpy(all_targets_sample.mean(axis=0).astype(np.float32))
        self.target_std = torch.from_numpy(all_targets_sample.std(axis=0).astype(np.float32) + 1e-8)
        
        print(f"[INFO] Feature mean shape: {self.feature_mean.shape}")
    
    def _get_features(self, file_idx, time_idx):
        """获取单个时间步的特征向量"""
        data = self.all_data[file_idx]
        
        # Auto-regressive: previous velocity (t-1)
        if time_idx > 0:
            prev_vel = data['pos_increment'][time_idx - 1]
        else:
            prev_vel = np.zeros(3, dtype=np.float32)
        
        features = np.concatenate([
            data['joint_pos'][time_idx],      # 23
            data['joint_vel'][time_idx],      # 23
            data['gyro_ang_vel'][time_idx],   # 3
            data['gravity_vec'][time_idx],    # 3
            data['joint_commands'][time_idx], # 23
            prev_vel,                         # 3 (from t-1)
        ])
        
        return features
    
    def get_file_data(self, file_idx):
        """获取整个文件的所有数据，用于递归推理评估"""
        data = self.all_data[file_idx]
        
        # 提取各个特征分量
        joint_pos = data['joint_pos']
        joint_vel = data['joint_vel']
        gyro = data['gyro_ang_vel']
        grav = data['gravity_vec']
        cmd = data['joint_commands']
        targets = data['pos_increment']
        
        return joint_pos, joint_vel, gyro, grav, cmd, targets
    
    def __len__(self):
        return len(self.sample_indices)
    
    def __getitem__(self, idx):
        file_idx, start_idx = self.sample_indices[idx]
        data = self.all_data[file_idx]
        
        # 获取历史窗口的特征
        # 整个窗口序列: t=start_idx 到 t=start_idx+history_len-1
        # 每个时刻 t 的输入特征包含 prev_vel (即 pos_increment[t-1])
        history_features = []
        for t in range(start_idx, start_idx + self.history_len):
            features = self._get_features(file_idx, t)
            history_features.append(features)
        
        history_features = np.stack(history_features, axis=0)  # (history_len, feature_dim)
        
        # 获取目标位置增量 (预测当前时刻 t=start_idx+history_len-1)
        target_idx = start_idx + self.history_len - 1
        target = data['pos_increment'][target_idx]
        
        # 转换为tensor
        history_features = torch.from_numpy(history_features.astype(np.float32))
        target = torch.from_numpy(target.astype(np.float32))
        
        return history_features, target


# ============================================================================
# 模型定义 - 基于论文架构
# ============================================================================
class ResidualCausalBlock(nn.Module):
    """
    TCN 残差块: 
    Input -> [DilatedAlpha -> Norm -> ELU -> Dropout] x2 -> + -> Output
          |                                            |
          ---------------- (Res) -----------------------
    """
    def __init__(self, n_inputs, n_outputs, kernel_size, dilation, dropout=0.2):
        super().__init__()
        
        # 确保因果填充: padding = (k-1)*d
        self.pad = (kernel_size - 1) * dilation
        
        self.conv1 = nn.utils.weight_norm(nn.Conv1d(n_inputs, n_outputs, kernel_size, dilation=dilation))
        self.norm1 = nn.LayerNorm(n_outputs)
        self.relu1 = nn.ELU()
        self.dropout1 = nn.Dropout(dropout)
        
        self.conv2 = nn.utils.weight_norm(nn.Conv1d(n_outputs, n_outputs, kernel_size, dilation=dilation))
        self.norm2 = nn.LayerNorm(n_outputs)
        self.relu2 = nn.ELU()
        self.dropout2 = nn.Dropout(dropout)
        
        self.downsample = nn.Conv1d(n_inputs, n_outputs, 1) if n_inputs != n_outputs else None
        self.relu_out = nn.ELU()

    def forward(self, x):
        # x: (Batch, Channels, Time)
        residual = x
        
        # Layer 1
        out = nn.functional.pad(x, (self.pad, 0))
        out = self.conv1(out)
        # LayerNorm expects (Batch, Time, Channels), so we transpose
        out = out.transpose(1, 2)
        out = self.norm1(out)
        out = out.transpose(1, 2)
        out = self.relu1(out)
        out = self.dropout1(out)
        
        # Layer 2
        out = nn.functional.pad(out, (self.pad, 0))
        out = self.conv2(out)
        out = out.transpose(1, 2)
        out = self.norm2(out)
        out = out.transpose(1, 2)
        out = self.relu2(out)
        out = self.dropout2(out)
        
        # Residual connection
        if self.downsample is not None:
            residual = self.downsample(x)
            
        return self.relu_out(out + residual)


class TemporalEncoder(nn.Module):
    """
    时序编码器 (Residual TCN)
    """
    
    def __init__(self, input_dim, hidden_dim=128, num_layers=3, kernel_size=3, dropout=0.1):
        super().__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        
        layers = []
        # 将输入映射到 hidden_dim
        layers.append(nn.Conv1d(input_dim, hidden_dim, 1))
        
        # 堆叠残差块
        for i in range(num_layers):
            dilation = 2 ** i
            layers.append(ResidualCausalBlock(hidden_dim, hidden_dim, kernel_size, dilation, dropout))
            
        self.net = nn.Sequential(*layers)
        
    def forward(self, x):
        """
        Args:
            x: (batch, seq_len, input_dim)
        Returns:
            hidden: (batch, hidden_dim) - 最后一个时间步的特征
        """
        # TCN 需要 (Batch, Channels, Length)
        x = x.transpose(1, 2)
        
        # 前向传播
        out = self.net(x)
        
        # 转回 (Batch, Length, Channels)
        out = out.transpose(1, 2)
        
        # 返回最后一个时间步
        return out[:, -1, :]


class VelocityEstimator(nn.Module):
    """
    速度估计器 (Stage 1 网络)
    预测机器人在局部坐标系下的速度/位置增量
    """
    
    def __init__(self, hidden_dim=128, output_dim=3, dropout=0.1):
        super().__init__()
        
        self.velocity_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.ELU(),
            nn.Linear(hidden_dim // 2, output_dim),
        )
    
    def forward(self, x):
        """
        Args:
            x: (batch, hidden_dim)
        Returns:
            velocity: (batch, 3)
        """
        return self.velocity_head(x)


class AutoOdomNet(nn.Module):
    """
    完整的 AutoOdom Stage 1 网络
    """
    
    def __init__(self, input_dim, hidden_dim=128, num_layers=3, output_dim=3, kernel_size=5, dropout=0.1):
        super().__init__()
        
        self.encoder = TemporalEncoder(input_dim, hidden_dim, num_layers, kernel_size, dropout)
        self.velocity_estimator = VelocityEstimator(hidden_dim, output_dim, dropout)
        
        # 初始化权重
        self._init_weights()
    
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.orthogonal_(m.weight, gain=np.sqrt(2))
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
    
    def forward(self, x):
        """
        Args:
            x: (batch, seq_len, input_dim)
        Returns:
            velocity: (batch, 3) - 预测的位置增量/速度
        """
        hidden = self.encoder(x)
        velocity = self.velocity_estimator(hidden)
        return velocity


# ============================================================================
# 损失函数
# ============================================================================
class AutoOdomLoss(nn.Module):
    """
    AutoOdom 损失函数
    结合 L1、L2 和 Smooth L1 损失
    """
    
    def __init__(self, l1_weight=0.5, l2_weight=0.5, smooth_l1_weight=1.0):
        super().__init__()
        self.l1_weight = l1_weight
        self.l2_weight = l2_weight
        self.smooth_l1_weight = smooth_l1_weight
        self.l1_loss = nn.L1Loss()
        self.l2_loss = nn.MSELoss()
        self.smooth_l1_loss = nn.SmoothL1Loss(beta=0.01)  # Huber损失
    
    def forward(self, pred, target):
        l1 = self.l1_loss(pred, target)
        l2 = self.l2_loss(pred, target)
        smooth_l1 = self.smooth_l1_loss(pred, target)
        
        total_loss = self.l1_weight * l1 + self.l2_weight * l2 + self.smooth_l1_weight * smooth_l1
        
        return total_loss, {'l1': l1.item(), 'l2': l2.item(), 'rmse': np.sqrt(l2.item())}


# ============================================================================
# 训练器
# ============================================================================
class AutoOdomTrainer:
    def __init__(self, model, train_loader, val_loader, criterion, optimizer, 
                 scheduler=None, device='cuda', save_dir='./checkpoints',
                 feature_mean=None, feature_std=None, target_mean=None, target_std=None):
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.criterion = criterion
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.device = device
        self.save_dir = save_dir
        
        # 归一化参数
        self.feature_mean = feature_mean.to(device) if feature_mean is not None else None
        self.feature_std = feature_std.to(device) if feature_std is not None else None
        self.target_mean = target_mean.to(device) if target_mean is not None else None
        self.target_std = target_std.to(device) if target_std is not None else None
        
        os.makedirs(save_dir, exist_ok=True)
        
        self.train_losses = []
        self.val_losses = []
        self.best_val_loss = float('inf')
    
    def normalize_features(self, x):
        """归一化输入特征"""
        if self.feature_mean is not None:
            return (x - self.feature_mean) / self.feature_std
        return x
    
    def denormalize_target(self, y):
        """反归一化目标"""
        if self.target_mean is not None:
            return y * self.target_std + self.target_mean
        return y
        
    def train_epoch(self, epoch):
        self.model.train()
        total_loss = 0
        total_l1 = 0
        total_l2 = 0
        
        pbar = tqdm(self.train_loader, desc=f"Epoch {epoch} [Train]")
        for batch_idx, (data, target) in enumerate(pbar):
            data = data.to(self.device)
            target = target.to(self.device)
            
            # 归一化
            data = self.normalize_features(data)
            
            self.optimizer.zero_grad()
            output = self.model(data)
            loss, loss_dict = self.criterion(output, target)
            
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            
            total_loss += loss.item()
            total_l1 += loss_dict['l1']
            total_l2 += loss_dict['l2']
            
            pbar.set_postfix({
                'loss': f"{loss.item():.6f}",
                'rmse': f"{loss_dict['rmse']:.6f}"
            })
        
        avg_loss = total_loss / len(self.train_loader)
        avg_l1 = total_l1 / len(self.train_loader)
        avg_l2 = total_l2 / len(self.train_loader)
        
        return avg_loss, {'l1': avg_l1, 'l2': avg_l2, 'rmse': np.sqrt(avg_l2)}
    
    @torch.no_grad()
    def validate(self, epoch):
        self.model.eval()
        total_loss = 0
        total_l1 = 0
        total_l2 = 0
        
        pbar = tqdm(self.val_loader, desc=f"Epoch {epoch} [Val]")
        for data, target in pbar:
            data = data.to(self.device)
            target = target.to(self.device)
            
            data = self.normalize_features(data)
            
            output = self.model(data)
            loss, loss_dict = self.criterion(output, target)
            
            total_loss += loss.item()
            total_l1 += loss_dict['l1']
            total_l2 += loss_dict['l2']
        
        avg_loss = total_loss / len(self.val_loader)
        avg_l1 = total_l1 / len(self.val_loader)
        avg_l2 = total_l2 / len(self.val_loader)
        
        return avg_loss, {'l1': avg_l1, 'l2': avg_l2, 'rmse': np.sqrt(avg_l2)}
    
    def save_checkpoint(self, epoch, is_best=False):
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'train_losses': self.train_losses,
            'val_losses': self.val_losses,
            'best_val_loss': self.best_val_loss,
            'feature_mean': self.feature_mean.cpu() if self.feature_mean is not None else None,
            'feature_std': self.feature_std.cpu() if self.feature_std is not None else None,
            'target_mean': self.target_mean.cpu() if self.target_mean is not None else None,
            'target_std': self.target_std.cpu() if self.target_std is not None else None,
        }
        
        if self.scheduler:
            checkpoint['scheduler_state_dict'] = self.scheduler.state_dict()
        
        torch.save(checkpoint, os.path.join(self.save_dir, 'auto_odom_stage1_last.pth'))
        
        if is_best:
            torch.save(checkpoint, os.path.join(self.save_dir, 'auto_odom_stage1_best.pth'))
            print(f"  [BEST] Saved best model with val_loss: {self.best_val_loss:.6f}")
    
    def train(self, num_epochs):
        print(f"\n{'='*60}")
        print(f"AutoOdom Stage 1 Training")
        print(f"{'='*60}")
        print(f"Device: {self.device}")
        print(f"Model parameters: {sum(p.numel() for p in self.model.parameters()):,}")
        print(f"Training samples: {len(self.train_loader.dataset)}")
        print(f"Validation samples: {len(self.val_loader.dataset)}")
        print(f"{'='*60}\n")
        
        for epoch in range(1, num_epochs + 1):
            # 训练
            train_loss, train_metrics = self.train_epoch(epoch)
            self.train_losses.append(train_loss)
            
            # 验证
            val_loss, val_metrics = self.validate(epoch)
            self.val_losses.append(val_loss)
            
            # 学习率调度
            if self.scheduler:
                self.scheduler.step()
            
            # 打印信息
            current_lr = self.optimizer.param_groups[0]['lr']
            print(f"\n[Epoch {epoch}/{num_epochs}]")
            print(f"  Train - Loss: {train_loss:.6f} | L1: {train_metrics['l1']:.6f} | RMSE: {train_metrics['rmse']:.6f}")
            print(f"  Val   - Loss: {val_loss:.6f} | L1: {val_metrics['l1']:.6f} | RMSE: {val_metrics['rmse']:.6f}")
            print(f"  LR: {current_lr:.2e}")
            
            # 保存模型
            is_best = val_loss < self.best_val_loss
            if is_best:
                self.best_val_loss = val_loss
            self.save_checkpoint(epoch, is_best)
        
        self.plot_training_curves()
        
        return self.train_losses, self.val_losses
    
    def plot_training_curves(self):
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Loss曲线
        axes[0].plot(self.train_losses, label='Train Loss', color='blue')
        axes[0].plot(self.val_losses, label='Val Loss', color='red')
        axes[0].set_xlabel('Epoch')
        axes[0].set_ylabel('Loss')
        axes[0].set_title('Training and Validation Loss')
        axes[0].legend()
        axes[0].grid(True)
        
        # Log scale
        axes[1].plot(self.train_losses, label='Train Loss', color='blue')
        axes[1].plot(self.val_losses, label='Val Loss', color='red')
        axes[1].set_xlabel('Epoch')
        axes[1].set_ylabel('Loss (log scale)')
        axes[1].set_title('Training and Validation Loss (Log Scale)')
        axes[1].set_yscale('log')
        axes[1].legend()
        axes[1].grid(True)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.save_dir, 'training_curves.png'), dpi=300)
        plt.close()
        print(f"[INFO] Training curves saved to {self.save_dir}/training_curves.png")


# ============================================================================
# 评估函数
# ============================================================================
@torch.no_grad()
def evaluate_model(model, test_loader, device='cuda', feature_mean=None, feature_std=None):
    """评估模型性能"""
    model.eval()
    
    all_preds = []
    all_targets = []
    
    if feature_mean is not None:
        feature_mean = feature_mean.to(device)
        feature_std = feature_std.to(device)
    
    for data, target in tqdm(test_loader, desc="Evaluating"):
        data = data.to(device)
        
        if feature_mean is not None:
            data = (data - feature_mean) / feature_std
        
        output = model(data)
        
        all_preds.append(output.cpu().numpy())
        all_targets.append(target.numpy())
    
    all_preds = np.concatenate(all_preds, axis=0)
    all_targets = np.concatenate(all_targets, axis=0)
    
    # 计算误差指标
    mse = np.mean((all_preds - all_targets) ** 2)
    mae = np.mean(np.abs(all_preds - all_targets))
    rmse = np.sqrt(mse)
    
    # 分轴误差
    mae_per_axis = np.mean(np.abs(all_preds - all_targets), axis=0)
    
    print(f"\n{'='*50}")
    print(f"Evaluation Results (Step-wise)")
    print(f"{'='*50}")
    print(f"MSE:  {mse:.6f}")
    print(f"MAE:  {mae:.6f}")
    print(f"RMSE: {rmse:.6f}")
    print(f"MAE per axis (x, y, z): [{mae_per_axis[0]:.6f}, {mae_per_axis[1]:.6f}, {mae_per_axis[2]:.6f}]")
    print(f"{'='*50}")
    
    return {
        'mse': mse, 'mae': mae, 'rmse': rmse,
        'mae_per_axis': mae_per_axis,
        'predictions': all_preds, 'targets': all_targets
    }


def evaluate_recursive(model, dataset, file_indices, device='cuda', save_path=None):
    """
    执行递归推理评估 (Closed-loop Evaluation)
    
    Args:
        model: 训练好的模型
        dataset: 数据集实例
        file_indices: 要评估的文件索引列表
        device: 计算设备
        save_path: 结果保存路径
    """
    model.eval()
    
    total_ate = 0
    total_samples = 0
    all_results = {'predictions': [], 'targets': []}
    
    mean = dataset.feature_mean.to(device)
    std = dataset.feature_std.to(device)
    
    print(f"\n[INFO] Starting Recursive Evaluation on {len(file_indices)} files...")
    
    with torch.no_grad():
        for i, file_idx in enumerate(file_indices):
            # 获取单条轨迹的所有数据
            joint_pos, joint_vel, gyro, grav, cmd, targets = dataset.get_file_data(file_idx)
            
            # 转为 tensor
            T = len(joint_pos)
            # 预分配特征矩阵 (不需要 prev_vel，因为它是动态填充的)
            # Proprioceptive static features for all timesteps
            # (T, 75)
            proprio_feats = np.concatenate([joint_pos, joint_vel, gyro, grav, cmd], axis=1)
            proprio_feats = torch.from_numpy(proprio_feats).float().to(device)
            
            # 准备输出buffer
            preds = np.zeros_like(targets)
            
            # 历史 Buffer (用于 TCN)
            # 我们维护一个滑窗 buffer: (Batch=1, SeqLen, InputDim)
            # 初始时刻: 用真实历史填充前 history_len 帧 (或者用0初始化，根据论文通常前几帧给GT)
            # 这里我们用前 history_len 帧的 GT 来启动
            start_t = dataset.history_len
            
            # 填充初始 GT 到 buffer
            # 注意: Dataset.__getitem__ 逻辑是:
            # features[t] = [proprio[t], prev_vel[t]] where prev_vel[t] = pos_inc[t-1]
            
            current_window = []
            
            # 初始化 window 0 to start_t-1
            for t in range(start_t):
                if t == 0:
                    pv = np.zeros(3, dtype=np.float32)
                else:
                    pv = targets[t-1]
                
                # 拼接特征
                feat = torch.cat([proprio_feats[t], torch.from_numpy(pv).to(device)])
                current_window.append(feat)
                
                # 记录前几帧的预测直接为 GT (Warmup)
                preds[t] = targets[t]
            
            # 转为 Tensor Buffer: (HistoryLen, InputDim)
            window_tensor = torch.stack(current_window)
            
            # 开始递归推理
            for t in range(start_t, T):
                # 1. 准备输入: (1, HistoryLen, Dim)
                input_seq = window_tensor.unsqueeze(0)
                
                # 2. 归一化
                input_seq = (input_seq - mean) / std
                
                # 3. 前向传播
                pred_vel = model(input_seq) # (1, 3)
                pred_vel_np = pred_vel.cpu().numpy()[0]
                preds[t] = pred_vel_np
                
                # 4. 更新 Window
                # 下一时刻 (t+1) 需要的特征: features[t+1] = [proprio[t+1], pred_vel[t]]
                # 哎呀，这里TCN只需要当前时刻 t 的输出? 
                # 不，TCN 在时刻 t 预测 v_t。
                # 下一时刻 t+1，TCN 需要输入 history window ending at t+1.
                # window 的最后一个元素是 feature[t+1]? 
                # 不，dataset.__getitem__ 取 range(start, start+history_len)
                # target 是 pos_increment[start+history_len-1] (即 window 最后一个时刻的输出)
                # 所以，为了预测 t，我们需要 features[t-history_len+1 ... t]
                # feature[k] 包括 [proprio[k], v_{k-1}]
                # 所以为了预测preds[t]，我们需要 feature[t]，其包含了 v_{t-1} (即 preds[t-1])
                
                if t < T - 1: # 还有下一帧需要预测
                    # 构造 feature[t+1] 的一部分: prev_vel = preds[t]
                    # 但我们需要保持 window 滚动。
                    # window 当前是 feat[t-H+1] ... feat[t]
                    # 下一步需要 feat[t-H+2] ... feat[t+1]
                    # feat[t+1] 需要 proprio[t+1] 和 prev_vel (即 preds[t])
                    
                    # 获取下一个 proprio
                    next_proprio = proprio_feats[t+1] # GPU tensor
                    
                    # 获取当前预测作为下一个 prev_vel
                    # 注意: 这里是否需要反归一化?
                    # 模型的输出是 Raw Metric，如前所述。
                    # 下一时刻的输入特征中 prev_vel 就应该是这个 Raw Metric。
                    # 稍后归一化会处理它。
                    next_prev_vel = pred_vel[0] # GPU tensor
                    
                    next_feat = torch.cat([next_proprio, next_prev_vel])
                    
                    # 滚动 buffer
                    window_tensor = torch.cat([window_tensor[1:], next_feat.unsqueeze(0)], dim=0)
            
            # 计算该轨迹的指标
            # 仅计算从 start_t 开始的部分，因为前面是 Warmup GT
            valid_preds = preds[start_t:]
            valid_targets = targets[start_t:]
            
            # 累积误差 (ATE)
            # 重建轨迹
            # 注意: 每一帧是 pos_increment (Local velocity * dt in loose terms, or Local delta)
            # 要计算 ATE，应该在 Global Frame 累积，但这需要 Orientation。
            # 既然只有 Local pos_increment，我们只能对比 "Dead Reckoning" 轨迹
            # 假设 Orientation 是完美的 (使用 GT Rotation 积分) 或者简化为仅累积 Local 增量 (如果它是 2D 平面且忽略旋转)
            # 但 Paper 通常指 local frame velocity estimation accuracy.
            # 这里的 evaluation code 之前的逻辑是简单的 cumsum (Assuming pure translation alignment roughly?)
            # 让我们保持一致性，使用 cumsum on raw output (Local Path Integration)
            
            pred_path = np.cumsum(valid_preds, axis=0)
            target_path = np.cumsum(valid_targets, axis=0)
            
            path_err = np.sqrt(np.sum((pred_path - target_path)**2, axis=1))
            ate = np.mean(path_err)
            
            total_ate += ate
            total_samples += 1
            
            all_results['predictions'].append(valid_preds)
            all_results['targets'].append(valid_targets)
            
    avg_ate = total_ate / total_samples
    print(f"[INFO] Recursive Evaluation ATE: {avg_ate:.4f} m (over {total_samples} trajectories)")
    
    # 合并结果用于绘图 (只取第一个轨迹或合并所有)
    concat_preds = np.concatenate(all_results['predictions'], axis=0)
    concat_targets = np.concatenate(all_results['targets'], axis=0)
    
    return {
        'ate': avg_ate,
        'predictions': concat_preds,
        'targets': concat_targets
    }


def plot_results(results, save_path='results.png'):
    """绘制评估结果"""
    # 兼容处理: 限制绘图点数，避免 batch mode 下过大
    preds = results['predictions']
    targets = results['targets']
    
    max_plot_pts = 10000
    if len(preds) > max_plot_pts:
        preds = preds[:max_plot_pts]
        targets = targets[:max_plot_pts]
        
    pred_trajectory = np.cumsum(preds, axis=0)
    target_trajectory = np.cumsum(targets, axis=0)
    t = np.arange(len(preds))
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    
    # X-Y 轨迹
    ax = axes[0, 0]
    ax.plot(target_trajectory[:, 0], target_trajectory[:, 1], 'b-', linewidth=2, label='Ground Truth')
    ax.plot(pred_trajectory[:, 0], pred_trajectory[:, 1], 'r--', linewidth=2, label='Prediction')
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_title('Trajectory (Segment)')
    ax.legend()
    ax.grid(True)
    ax.axis('equal')
    
    # X 坐标
    ax = axes[0, 1]
    t = np.arange(len(target_trajectory))
    ax.plot(t, target_trajectory[:, 0], 'b-', label='GT X')
    ax.plot(t, pred_trajectory[:, 0], 'r--', label='Pred X')
    ax.set_xlabel('Time Step')
    ax.set_ylabel('X (m)')
    ax.set_title('X Coordinate')
    ax.legend()
    ax.grid(True)
    
    # Y 坐标
    ax = axes[0, 2]
    ax.plot(t, target_trajectory[:, 1], 'b-', label='GT Y')
    ax.plot(t, pred_trajectory[:, 1], 'r--', label='Pred Y')
    ax.set_xlabel('Time Step')
    ax.set_ylabel('Y (m)')
    ax.set_title('Y Coordinate')
    ax.legend()
    ax.grid(True)
    
    # 位置增量误差分布
    ax = axes[1, 0]
    errors = results['predictions'] - results['targets']
    ax.hist(errors[:, 0], bins=50, alpha=0.7, label='X error')
    ax.hist(errors[:, 1], bins=50, alpha=0.7, label='Y error')
    ax.hist(errors[:, 2], bins=50, alpha=0.7, label='Z error')
    ax.set_xlabel('Error (m)')
    ax.set_ylabel('Count')
    ax.set_title('Prediction Error Distribution')
    ax.legend()
    ax.grid(True)
    
    # 累积轨迹误差
    ax = axes[1, 1]
    trajectory_error = np.sqrt(np.sum((pred_trajectory - target_trajectory) ** 2, axis=1))
    ax.plot(t, trajectory_error, 'purple')
    ax.fill_between(t, 0, trajectory_error, alpha=0.3, color='purple')
    ax.set_xlabel('Time Step')
    ax.set_ylabel('Position Error (m)')
    ax.set_title('Cumulative Trajectory Error')
    ax.grid(True)
    
    # 速度/增量对比
    ax = axes[1, 2]
    ax.scatter(results['targets'][:, 0], results['predictions'][:, 0], alpha=0.1, s=1, label='X')
    ax.scatter(results['targets'][:, 1], results['predictions'][:, 1], alpha=0.1, s=1, label='Y')
    ax.plot([-0.02, 0.02], [-0.02, 0.02], 'k--', linewidth=1)
    ax.set_xlabel('Ground Truth')
    ax.set_ylabel('Prediction')
    ax.set_title('Prediction vs Ground Truth')
    ax.legend()
    ax.grid(True)
    ax.axis('equal')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"[INFO] Results saved to {save_path}")


# ============================================================================
# 主函数
# ============================================================================
def parse_args():
    parser = argparse.ArgumentParser(description="AutoOdom Stage 1 Training")
    
    # 数据参数
    parser.add_argument('--data_dir', type=str, 
                        default='/home/dogogod/robot_lab/Test',
                        help='数据目录路径')
    parser.add_argument('--history_len', type=int, default=50,
                        help='历史窗口长度 (论文中使用50)')
    
    # 模型参数
    parser.add_argument('--hidden_dim', type=int, default=128,
                        help='隐藏层维度')
    parser.add_argument('--num_layers', type=int, default=3,
                        help='TCN层数')
    parser.add_argument('--kernel_size', type=int, default=5,
                        help='TCN卷积核大小')
    parser.add_argument('--dropout', type=float, default=0.1,
                        help='Dropout率')
    
    # 训练参数
    parser.add_argument('--batch_size', type=int, default=256,
                        help='批次大小')
    parser.add_argument('--num_epochs', type=int, default=200,
                        help='训练轮数')
    parser.add_argument('--lr', type=float, default=5e-4,
                        help='学习率')
    parser.add_argument('--weight_decay', type=float, default=1e-5,
                        help='权重衰减')
    parser.add_argument('--warmup_epochs', type=int, default=10,
                        help='学习率预热轮数')
    
    # 其他参数
    parser.add_argument('--device', type=str, default='cuda',
                        help='设备 (cuda/cpu)')
    parser.add_argument('--save_dir', type=str, 
                        default='/home/dogogod/robot_lab/Test',
                        help='模型保存目录')
    parser.add_argument('--seed', type=int, default=42,
                        help='随机种子')
    parser.add_argument('--val_split', type=float, default=0.1,
                        help='验证集比例')
    parser.add_argument('--eval_only', action='store_true',
                        help='仅评估模式')
    parser.add_argument('--checkpoint', type=str, default=None,
                        help='加载的checkpoint路径')
    
    return parser.parse_args()


def main():
    import random
    args = parse_args()
    
    # 设置随机种子
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(args.seed)
    
    device = torch.device(args.device if torch.cuda.is_available() else 'cpu')
    print(f"[INFO] Using device: {device}")
    
    # 1. 获取文件列表
    all_files = sorted(glob.glob(os.path.join(args.data_dir, "booster_t1_stage1_data_*.npz")))
    if not all_files:
        print(f"[ERROR] No data files found in {args.data_dir}")
        return
        
    # 2. 按文件划分训练/验证集 (Data Splitting)
    # 打乱文件顺序
    random.shuffle(all_files)
    
    val_count = max(1, int(len(all_files) * args.val_split))
    train_files = all_files[val_count:]
    val_files = all_files[:val_count]
    
    print(f"\n[INFO] Total files: {len(all_files)}")
    print(f"[INFO] Train files: {len(train_files)}")
    print(f"[INFO] Val files:   {len(val_files)}")
    
    # 3. 创建数据集
    # 训练集: 计算统计量
    print(f"\n[INFO] Creating TRAIN dataset...")
    train_dataset = AutoOdomDataset(
        data_files=train_files,
        history_len=args.history_len,
        compute_stats=True
    )
    
    # 验证集: 使用训练集的统计量
    print(f"\n[INFO] Creating VAL dataset...")
    val_dataset = AutoOdomDataset(
        data_files=val_files,
        history_len=args.history_len,
        compute_stats=False,
        feature_mean=train_dataset.feature_mean,
        feature_std=train_dataset.feature_std,
        target_mean=train_dataset.target_mean,
        target_std=train_dataset.target_std
    )
    
    print(f"[INFO] Train samples: {len(train_dataset)}")
    print(f"[INFO] Val samples: {len(val_dataset)}")
    
    # 创建数据加载器
    train_loader = DataLoader(
        train_dataset, batch_size=args.batch_size,
        shuffle=True, num_workers=4, pin_memory=True
    )
    
    val_loader = DataLoader(
        val_dataset, batch_size=args.batch_size,
        shuffle=False, num_workers=4, pin_memory=True
    )
    
    # 创建模型
    model = AutoOdomNet(
        input_dim=train_dataset.input_dim,
        hidden_dim=args.hidden_dim,
        num_layers=args.num_layers,
        kernel_size=args.kernel_size,
        output_dim=3,
        dropout=args.dropout
    )
    
    print(f"\n[INFO] Model Architecture:")
    print(model)
    print(f"\n[INFO] Total parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # 加载checkpoint (如果有)
    if args.checkpoint:
        print(f"[INFO] Loading checkpoint from {args.checkpoint}")
        checkpoint = torch.load(args.checkpoint, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
    
    # 评估模式
    if args.eval_only:
        model.to(device)
        # 确保使用正确的统计量 (如果loaded checkpont有的话最好用checkpoint的，这里简单起见用当前dataset的)
        results = evaluate_model(
            model, val_loader, device,
            train_dataset.feature_mean, train_dataset.feature_std
        )
        plot_results(results, os.path.join(args.save_dir, 'eval_results.png'))
        return
    
    # 创建优化器
    optimizer = optim.AdamW(
        model.parameters(),
        lr=args.lr,
        weight_decay=args.weight_decay,
        betas=(0.9, 0.999)
    )
    
    # 使用CosineAnnealingWarmRestarts + warmup (保持原逻辑)
    def lr_lambda(epoch):
        if epoch < args.warmup_epochs:
            # 线性warmup
            return (epoch + 1) / args.warmup_epochs
        else:
            # 余弦退火
            progress = (epoch - args.warmup_epochs) / (args.num_epochs - args.warmup_epochs)
            return 0.5 * (1.0 + np.cos(np.pi * progress))
    
    scheduler = optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    
    criterion = AutoOdomLoss(l1_weight=0.5, l2_weight=0.5, smooth_l1_weight=1.0)
    
    # 创建训练器
    trainer = AutoOdomTrainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        criterion=criterion,
        optimizer=optimizer,
        scheduler=scheduler,
        device=device,
        save_dir=args.save_dir,
        feature_mean=train_dataset.feature_mean,
        feature_std=train_dataset.feature_std,
        target_mean=train_dataset.target_mean,
        target_std=train_dataset.target_std
    )
    
    # 训练
    trainer.train(args.num_epochs)
    
    # 最终评估
    print("\n" + "="*60)
    print("Final Evaluation with Best Model")
    print("="*60)
    
    best_ckpt = torch.load(os.path.join(args.save_dir, 'auto_odom_stage1_best.pth'))
    model.load_state_dict(best_ckpt['model_state_dict'])
    model.to(device)
    
    # 从checkpoint恢复统计量
    loaded_mean = best_ckpt.get('feature_mean', train_dataset.feature_mean).to(device)
    loaded_std = best_ckpt.get('feature_std', train_dataset.feature_std).to(device)
    
    # 更新 dataset 的统计量以便 recursive eval 使用
    val_dataset.feature_mean = loaded_mean
    val_dataset.feature_std = loaded_std
    
    # 1. 常规 Batch 评估 (One-step prediction)
    print("\n[Mode 1] Standard Batch Evaluation (Teacher Forcing)...")
    results = evaluate_model(
        model, val_loader, device,
        loaded_mean, loaded_std
    )
    
    # 2. 递归评估 (Recursive / Closed-loop)
    # 随机抽取部分验证集文件进行评估 (例如 10 个)
    print("\n[Mode 2] Recursive Trajectory Evaluation (Closed-loop)...")
    num_eval_files = min(10, len(val_files))
    # indices in val_dataset correspond to file indices in val_files list?
    # No, val_dataset was created with a list of files.
    # Dataset internal indices 0..N-1 correspond exactly to the provided file list order 
    # IF the dataset implementation maps flat sample index to file index.
    # Wait, our Dataset logic flattens samples.
    # We added `get_file_data(file_idx)`. 
    # file_idx here refers to the index in `self.data_files`.
    # So we can just iterate 0..len(val_files)-1
    
    eval_file_indices = list(range(num_eval_files))
    
    recursive_results = evaluate_recursive(
        model, val_dataset, eval_file_indices, device
    )
    
    plot_results(recursive_results, os.path.join(args.save_dir, 'final_recursive_results.png'))
    
    print("\n[INFO] Training completed!")
    print(f"[INFO] Best model saved to {args.save_dir}/auto_odom_stage1_best.pth")


if __name__ == "__main__":
    main()
