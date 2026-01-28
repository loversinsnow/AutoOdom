#!/usr/bin/env python3
"""
AutoOdom Stage 1: Simulation-Based Pre-training
==================================================

根据论文 "AutoOdom: Sim-to-Real End-to-End Proprioceptive Odometry for Legged Robots"
实现 Stage 1 的训练程序。

Stage 1 目标:
- 使用仿真数据进行预训练
- 从本体感知信息 (proprioceptive) 预测局部坐标系下的位置增量
- 学习映射: f(A_t, v_cmd, ω, q, q_dot, R, Δp) → Δp_local

输入特征 (根据论文 Section III-A):
- joint_commands: 关节动作指令 A_t (12,)
- cmd_vel: 命令速度 v_cmd (3,) [v_x, v_y, ω_z]
- gyro_ang_vel: 陀螺仪角速度 ω (3,)
- joint_pos: 关节位置 q (12,)
- joint_vel: 关节速度 q_dot (12,)
- base_rot_mat: 旋转矩阵 R (3,3) -> 展平为 (6,)
- pos_increment_hist: 历史位移 Δp (2,) [仅推理时使用模型预测值]

输出 (Ground Truth):
- pos_increment_hist: 局部坐标系位移增量 (2,) [dx, dy] (仅平面运动)

损失函数:
- MSE Loss 用于位移预测

"""

import os
import glob
import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
from torch.utils.tensorboard import SummaryWriter
import time
from datetime import datetime


# =============================================================================
# 1. 数据集类定义
# =============================================================================
class AutoOdomDataset(Dataset):
    """
    AutoOdom 训练数据集
    
    加载 .npz 文件中的仿真数据，支持:
    - 单步预测: 输入当前帧特征，预测当前帧位移增量
    - 序列预测: 输入历史帧序列，预测当前位移增量 (可选)
    """
    
    def __init__(self, data_dir, file_pattern="Z1-*.npz", 
                 history_len=1, use_rotation_matrix=True,
                 max_files=None, normalize=True):
        """
        Args:
            data_dir: 数据目录路径
            file_pattern: 数据文件匹配模式
            history_len: 历史帧数量 (1=仅当前帧)
            use_rotation_matrix: 是否使用完整旋转矩阵 (False则提取重力向量)
            max_files: 最大加载文件数 (调试用)
            normalize: 是否对数据进行标准化
        """
        self.data_dir = data_dir
        self.history_len = history_len
        self.use_rotation_matrix = use_rotation_matrix
        self.normalize = normalize
        
        # 查找所有数据文件
        file_list = sorted(glob.glob(os.path.join(data_dir, file_pattern)))
        if max_files is not None:
            file_list = file_list[:max_files]
        
        if len(file_list) == 0:
            raise ValueError(f"在 {data_dir} 中未找到匹配 {file_pattern} 的文件")
        
        print(f"[Dataset] 找到 {len(file_list)} 个数据文件")
        
        # 加载所有数据
        all_joint_pos = []
        all_joint_vel = []
        all_gyro_ang_vel = []
        all_base_rot_mat = []
        all_pos_increment = []
        all_cmd_vel = []
        all_joint_commands = []
        
        for fpath in file_list:
            data = np.load(fpath)
            all_joint_pos.append(data['joint_pos'])
            all_joint_vel.append(data['joint_vel'])
            all_gyro_ang_vel.append(data['gyro_ang_vel'])
            all_base_rot_mat.append(data['base_rot_mat'])
            all_pos_increment.append(data['pos_increment_hist'])
            all_cmd_vel.append(data['cmd_vel'])
            all_joint_commands.append(data['joint_commands'])
        
        # 合并数据
        self.joint_pos = np.concatenate(all_joint_pos, axis=0).astype(np.float32)
        self.joint_vel = np.concatenate(all_joint_vel, axis=0).astype(np.float32)
        self.gyro_ang_vel = np.concatenate(all_gyro_ang_vel, axis=0).astype(np.float32)
        self.base_rot_mat = np.concatenate(all_base_rot_mat, axis=0).astype(np.float32)
        self.pos_increment = np.concatenate(all_pos_increment, axis=0).astype(np.float32)
        self.cmd_vel = np.concatenate(all_cmd_vel, axis=0).astype(np.float32)
        self.joint_commands = np.concatenate(all_joint_commands, axis=0).astype(np.float32)
        
        print(f"[Dataset] 总样本数: {len(self.joint_pos)}")
        print(f"  - joint_pos shape: {self.joint_pos.shape}")
        print(f"  - joint_vel shape: {self.joint_vel.shape}")
        print(f"  - gyro_ang_vel shape: {self.gyro_ang_vel.shape}")
        print(f"  - base_rot_mat shape: {self.base_rot_mat.shape}")
        print(f"  - pos_increment shape: {self.pos_increment.shape}")
        
        # 计算标准化参数
        if self.normalize:
            self._compute_normalization_stats()
        
        # 计算输入维度
        self._compute_input_dim()
    
    def _compute_normalization_stats(self):
        """计算各特征的均值和标准差用于标准化"""
        self.stats = {
            'joint_commands_mean': np.mean(self.joint_commands, axis=0),
            'joint_commands_std': np.std(self.joint_commands, axis=0) + 1e-8,
            'joint_pos_mean': np.mean(self.joint_pos, axis=0),
            'joint_pos_std': np.std(self.joint_pos, axis=0) + 1e-8,
            'joint_vel_mean': np.mean(self.joint_vel, axis=0),
            'joint_vel_std': np.std(self.joint_vel, axis=0) + 1e-8,
            'gyro_ang_vel_mean': np.mean(self.gyro_ang_vel, axis=0),
            'gyro_ang_vel_std': np.std(self.gyro_ang_vel, axis=0) + 1e-8,
            'cmd_vel_mean': np.mean(self.cmd_vel, axis=0),
            'cmd_vel_std': np.std(self.cmd_vel, axis=0) + 1e-8,
            'pos_increment_mean': np.mean(self.pos_increment, axis=0),
            'pos_increment_std': np.std(self.pos_increment, axis=0) + 1e-8,
        }
        
        print("[Dataset] 标准化统计:")
        print(f"  - pos_increment mean: {self.stats['pos_increment_mean']}")
        print(f"  - pos_increment std: {self.stats['pos_increment_std']}")
    
    def _compute_input_dim(self):
        """计算输入特征维度 (根据论文 Section III-A)"""
        # 论文输入: A_t(12) + v_cmd(3) + ω(3) + q(12) + q_dot(12) + R(6) + Δp(2)
        # joint_commands(12) + cmd_vel(3) + gyro_ang_vel(3) + joint_pos(12) + joint_vel(12)
        self.input_dim = 12 + 3 + 3 + 12 + 12
        
        if self.use_rotation_matrix:
            # 使用旋转矩阵的前两行 (6维)
            self.input_dim += 6
        else:
            # 使用重力向量 (3维)
            self.input_dim += 3
        
        # 历史位移 Δp (2维) - 论文中 Stage 1 用 GT，Stage 2 用模型预测
        self.input_dim += 2  # pos_increment_hist[:2]
        
        print(f"[Dataset] 输入特征维度: {self.input_dim} (论文配置: joint_commands(12)+cmd_vel(3)+gyro(3)+joint_pos(12)+joint_vel(12)+rot(6)+delta_p(2)=50)")
    
    def __len__(self):
        return len(self.joint_pos) - self.history_len + 1
    
    def __getitem__(self, idx):
        """
        获取单个样本
        
        Returns:
            features: 输入特征 (input_dim,) 或 (history_len, input_dim)
            target: 位移增量目标 (3,)
        """
        # 当前帧索引
        curr_idx = idx + self.history_len - 1
        
        # 提取特征 (按论文顺序: A_t, v_cmd, ω, q, q_dot, R, Δp)
        joint_commands = self.joint_commands[curr_idx]  # A_t: 动作指令
        cmd_vel = self.cmd_vel[curr_idx]                # v_cmd: 命令速度
        gyro_ang_vel = self.gyro_ang_vel[curr_idx]      # ω: 角速度
        joint_pos = self.joint_pos[curr_idx]            # q: 关节位置
        joint_vel = self.joint_vel[curr_idx]            # q_dot: 关节速度
        rot_mat = self.base_rot_mat[curr_idx]           # R: 旋转矩阵
        pos_inc_hist = self.pos_increment[curr_idx, :2] # Δp: 历史位移 (Stage1用GT)
        
        # 处理旋转矩阵
        if self.use_rotation_matrix:
            # 取前两行展平
            rot_features = rot_mat[:2, :].flatten()
        else:
            # 提取重力向量 (旋转矩阵第三列)
            rot_features = rot_mat[:, 2]
        
        # 标准化
        if self.normalize:
            joint_commands = (joint_commands - self.stats['joint_commands_mean']) / self.stats['joint_commands_std']
            cmd_vel = (cmd_vel - self.stats['cmd_vel_mean']) / self.stats['cmd_vel_std']
            gyro_ang_vel = (gyro_ang_vel - self.stats['gyro_ang_vel_mean']) / self.stats['gyro_ang_vel_std']
            joint_pos = (joint_pos - self.stats['joint_pos_mean']) / self.stats['joint_pos_std']
            joint_vel = (joint_vel - self.stats['joint_vel_mean']) / self.stats['joint_vel_std']
            # pos_inc_hist 不标准化，保持原始尺度 (论文中作为额外输入)
        
        # 拼接特征 (按论文顺序)
        features = np.concatenate([
            joint_commands, # 12 - A_t
            cmd_vel,        # 3  - v_cmd
            gyro_ang_vel,   # 3  - ω
            joint_pos,      # 12 - q
            joint_vel,      # 12 - q_dot
            rot_features,   # 6  - R (前两行)
            pos_inc_hist,   # 2  - Δp (历史位移)
        ]).astype(np.float32)
        
        # 目标: 当前帧的位移增量 (仅 x, y 两维)
        target = self.pos_increment[curr_idx, :2].astype(np.float32)
        
        return torch.from_numpy(features), torch.from_numpy(target)
    
    def get_normalization_stats(self):
        """返回标准化统计量，用于推理时"""
        return self.stats


# =============================================================================
# 2. 模型定义
# =============================================================================
class AutoOdomMLP(nn.Module):
    """
    AutoOdom Stage 1 MLP 模型
    
    简单的多层感知机用于位移预测
    """
    
    def __init__(self, input_dim, hidden_dims=[256, 128, 64], output_dim=2, dropout=0.1):
        """
        Args:
            input_dim: 输入特征维度
            hidden_dims: 隐藏层维度列表
            output_dim: 输出维度 (2 for dx, dy)
            dropout: Dropout 比率
        """
        super().__init__()
        
        layers = []
        prev_dim = input_dim
        
        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout)
            ])
            prev_dim = hidden_dim
        
        # 输出层
        layers.append(nn.Linear(prev_dim, output_dim))
        
        self.network = nn.Sequential(*layers)
        
        # 初始化权重
        self._init_weights()
    
    def _init_weights(self):
        """初始化网络权重"""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        """
        前向传播
        
        Args:
            x: 输入特征 (batch, input_dim)
        
        Returns:
            位移增量预测 (batch, 2) [dx, dy]
        """
        return self.network(x)


class AutoOdomLSTM(nn.Module):
    """
    AutoOdom Stage 1 LSTM 模型
    
    使用 LSTM 捕捉时序信息
    """
    
    def __init__(self, input_dim, hidden_dim=128, num_layers=2, output_dim=2, dropout=0.1):
        super().__init__()
        
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, output_dim)
        )
    
    def forward(self, x):
        """
        Args:
            x: (batch, seq_len, input_dim) 或 (batch, input_dim)
        """
        if x.dim() == 2:
            x = x.unsqueeze(1)  # 添加序列维度
        
        lstm_out, _ = self.lstm(x)
        # 取最后一个时间步的输出
        out = self.fc(lstm_out[:, -1, :])
        return out


class AutoOdomTransformer(nn.Module):
    """
    AutoOdom Stage 1 Transformer 模型
    
    使用自注意力机制处理序列数据
    """
    
    def __init__(self, input_dim, d_model=128, nhead=4, num_layers=2, 
                 output_dim=2, dropout=0.1):
        super().__init__()
        
        self.input_proj = nn.Linear(input_dim, d_model)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        self.fc = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.ReLU(),
            nn.Linear(d_model // 2, output_dim)
        )
    
    def forward(self, x):
        if x.dim() == 2:
            x = x.unsqueeze(1)
        
        x = self.input_proj(x)
        x = self.transformer(x)
        out = self.fc(x[:, -1, :])
        return out


# =============================================================================
# 3. 训练器类
# =============================================================================
class Stage1Trainer:
    """
    Stage 1 训练器
    
    负责:
    - 模型训练
    - 验证评估
    - 模型保存
    - TensorBoard 日志
    """
    
    def __init__(self, model, train_loader, val_loader, 
                 device, save_dir, lr=1e-3, weight_decay=1e-4):
        """
        Args:
            model: 待训练模型
            train_loader: 训练数据加载器
            val_loader: 验证数据加载器
            device: 计算设备
            save_dir: 模型保存目录
            lr: 学习率
            weight_decay: L2 正则化系数
        """
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.device = device
        self.save_dir = save_dir
        
        os.makedirs(save_dir, exist_ok=True)
        
        # 损失函数: MSE Loss
        self.criterion = nn.MSELoss()
        
        # 优化器: AdamW
        self.optimizer = optim.AdamW(
            model.parameters(), 
            lr=lr, 
            weight_decay=weight_decay
        )
        
        # 学习率调度器
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', factor=0.5, patience=10
        )
        
        # TensorBoard
        log_dir = os.path.join(save_dir, 'logs', datetime.now().strftime('%Y%m%d_%H%M%S'))
        self.writer = SummaryWriter(log_dir)
        
        # 最佳验证损失
        self.best_val_loss = float('inf')
        self.best_epoch = 0
    
    def train_epoch(self, epoch):
        """训练一个 epoch"""
        self.model.train()
        total_loss = 0.0
        num_batches = 0
        
        for batch_idx, (features, targets) in enumerate(self.train_loader):
            features = features.to(self.device)
            targets = targets.to(self.device)
            
            # 前向传播
            self.optimizer.zero_grad()
            predictions = self.model(features)
            
            # 计算损失
            loss = self.criterion(predictions, targets)
            
            # 反向传播
            loss.backward()
            
            # 梯度裁剪
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            
            self.optimizer.step()
            
            total_loss += loss.item()
            num_batches += 1
            
            if batch_idx % 100 == 0:
                print(f"  Batch {batch_idx}/{len(self.train_loader)}, Loss: {loss.item():.6f}")
        
        avg_loss = total_loss / num_batches
        return avg_loss
    
    def validate(self, epoch):
        """验证模型"""
        self.model.eval()
        total_loss = 0.0
        num_batches = 0
        
        all_preds = []
        all_targets = []
        
        with torch.no_grad():
            for features, targets in self.val_loader:
                features = features.to(self.device)
                targets = targets.to(self.device)
                
                predictions = self.model(features)
                loss = self.criterion(predictions, targets)
                
                total_loss += loss.item()
                num_batches += 1
                
                all_preds.append(predictions.cpu())
                all_targets.append(targets.cpu())
        
        avg_loss = total_loss / num_batches
        
        # 计算额外指标
        all_preds = torch.cat(all_preds, dim=0)
        all_targets = torch.cat(all_targets, dim=0)
        
        # 各维度 MAE
        mae = torch.abs(all_preds - all_targets).mean(dim=0)
        
        # 相对误差
        rel_error = torch.abs(all_preds - all_targets) / (torch.abs(all_targets) + 1e-8)
        mean_rel_error = rel_error.mean(dim=0)
        
        return avg_loss, mae, mean_rel_error
    
    def train(self, num_epochs, early_stop_patience=20):
        """
        完整训练流程
        
        Args:
            num_epochs: 最大训练轮数
            early_stop_patience: 早停耐心值
        """
        print(f"\n{'='*60}")
        print(f"开始 Stage 1 训练")
        print(f"{'='*60}")
        print(f"模型参数量: {sum(p.numel() for p in self.model.parameters()):,}")
        print(f"训练样本数: {len(self.train_loader.dataset)}")
        print(f"验证样本数: {len(self.val_loader.dataset)}")
        print(f"保存目录: {self.save_dir}")
        print(f"{'='*60}\n")
        
        patience_counter = 0
        
        for epoch in range(1, num_epochs + 1):
            start_time = time.time()
            
            print(f"Epoch {epoch}/{num_epochs}")
            print("-" * 40)
            
            # 训练
            train_loss = self.train_epoch(epoch)
            
            # 验证
            val_loss, val_mae, val_rel_error = self.validate(epoch)
            
            # 更新学习率
            self.scheduler.step(val_loss)
            
            epoch_time = time.time() - start_time
            
            # 打印结果
            print(f"  Train Loss: {train_loss:.6f}")
            print(f"  Val Loss: {val_loss:.6f}")
            print(f"  Val MAE: x={val_mae[0]:.6f}, y={val_mae[1]:.6f}")
            print(f"  Time: {epoch_time:.1f}s")
            
            # TensorBoard 记录
            self.writer.add_scalar('Loss/train', train_loss, epoch)
            self.writer.add_scalar('Loss/val', val_loss, epoch)
            self.writer.add_scalar('MAE/x', val_mae[0], epoch)
            self.writer.add_scalar('MAE/y', val_mae[1], epoch)
            self.writer.add_scalar('LR', self.optimizer.param_groups[0]['lr'], epoch)
            
            # 保存最佳模型
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.best_epoch = epoch
                patience_counter = 0
                
                # 保存模型
                save_path = os.path.join(self.save_dir, 'best_model.pth')
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                    'val_loss': val_loss,
                    'val_mae': val_mae.tolist(),
                }, save_path)
                print(f"  *** 保存最佳模型 (Val Loss: {val_loss:.6f}) ***")
            else:
                patience_counter += 1
            
            # 早停检查
            if patience_counter >= early_stop_patience:
                print(f"\n早停触发! 在 epoch {epoch} 停止训练")
                print(f"最佳验证损失: {self.best_val_loss:.6f} @ epoch {self.best_epoch}")
                break
            
            print()
        
        self.writer.close()
        
        print(f"\n{'='*60}")
        print(f"训练完成!")
        print(f"最佳验证损失: {self.best_val_loss:.6f} @ epoch {self.best_epoch}")
        print(f"模型保存于: {os.path.join(self.save_dir, 'best_model.pth')}")
        print(f"{'='*60}")


# =============================================================================
# 4. 主函数
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description='AutoOdom Stage 1 Training')
    
    # 数据参数
    parser.add_argument('--data_dir', type=str, 
                        default='/home/dogogod/magiclab_rl_lab/Data',
                        help='数据目录路径')
    parser.add_argument('--max_files', type=int, default=None,
                        help='最大加载文件数 (调试用)')
    
    # 模型参数
    parser.add_argument('--model_type', type=str, default='mlp',
                        choices=['mlp', 'lstm', 'transformer'],
                        help='模型类型')
    parser.add_argument('--hidden_dims', type=str, default='256,128,64',
                        help='MLP 隐藏层维度 (逗号分隔)')
    parser.add_argument('--dropout', type=float, default=0.1,
                        help='Dropout 比率')
    
    # 训练参数
    parser.add_argument('--batch_size', type=int, default=256,
                        help='批次大小')
    parser.add_argument('--epochs', type=int, default=100,
                        help='最大训练轮数')
    parser.add_argument('--lr', type=float, default=1e-3,
                        help='学习率')
    parser.add_argument('--weight_decay', type=float, default=1e-4,
                        help='L2 正则化系数')
    parser.add_argument('--val_split', type=float, default=0.1,
                        help='验证集比例')
    parser.add_argument('--early_stop', type=int, default=20,
                        help='早停耐心值')
    
    # 其他
    parser.add_argument('--device', type=str, default='cuda:0',
                        help='计算设备')
    parser.add_argument('--save_dir', type=str, default='checkpoints_stage1',
                        help='模型保存目录')
    parser.add_argument('--seed', type=int, default=42,
                        help='随机种子')
    
    args = parser.parse_args()
    
    # 设置随机种子
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(args.seed)
    
    # 设备
    device = torch.device(args.device if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")
    
    # 创建数据集
    print("\n加载数据...")
    dataset = AutoOdomDataset(
        data_dir=args.data_dir,
        max_files=args.max_files,
        normalize=True
    )
    
    # 划分训练/验证集
    val_size = int(len(dataset) * args.val_split)
    train_size = len(dataset) - val_size
    train_dataset, val_dataset = random_split(
        dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(args.seed)
    )
    
    print(f"训练集大小: {len(train_dataset)}")
    print(f"验证集大小: {len(val_dataset)}")
    
    # 创建数据加载器
    train_loader = DataLoader(
        train_dataset, 
        batch_size=args.batch_size, 
        shuffle=True,
        num_workers=4,
        pin_memory=True
    )
    val_loader = DataLoader(
        val_dataset, 
        batch_size=args.batch_size, 
        shuffle=False,
        num_workers=4,
        pin_memory=True
    )
    
    # 创建模型
    input_dim = dataset.input_dim
    hidden_dims = [int(x) for x in args.hidden_dims.split(',')]
    
    print(f"\n创建模型: {args.model_type}")
    
    if args.model_type == 'mlp':
        model = AutoOdomMLP(
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            output_dim=2,
            dropout=args.dropout
        )
    elif args.model_type == 'lstm':
        model = AutoOdomLSTM(
            input_dim=input_dim,
            hidden_dim=hidden_dims[0],
            num_layers=2,
            output_dim=2,
            dropout=args.dropout
        )
    else:  # transformer
        model = AutoOdomTransformer(
            input_dim=input_dim,
            d_model=hidden_dims[0],
            nhead=4,
            num_layers=2,
            output_dim=2,
            dropout=args.dropout
        )
    
    print(f"模型结构:\n{model}")
    
    # 保存目录 (使用完整路径)
    save_dir = os.path.join(args.data_dir, args.save_dir)
    
    # 保存标准化参数
    stats_path = os.path.join(save_dir, 'normalization_stats.npz')
    os.makedirs(save_dir, exist_ok=True)
    np.savez(stats_path, **dataset.get_normalization_stats())
    print(f"标准化参数已保存到: {stats_path}")
    
    # 创建训练器并开始训练
    trainer = Stage1Trainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        device=device,
        save_dir=save_dir,
        lr=args.lr,
        weight_decay=args.weight_decay
    )
    
    trainer.train(
        num_epochs=args.epochs,
        early_stop_patience=args.early_stop
    )


if __name__ == '__main__':
    main()
