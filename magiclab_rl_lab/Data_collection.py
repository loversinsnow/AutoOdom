import rclpy
from rclpy.node import Node
import numpy as np
import os
from scipy.spatial.transform import Rotation as R

# === 消息类型引入 ===
# 注意：如果你的机器人使用自定义消息（如 magicbot_msgs），请在此处修改 import
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Imu, JointState
# from magicbot_msgs.msg import LowState, LowCmd  # <--- 如果是自定义消息，请取消注释并使用这行

class DataCollector(Node):
    def __init__(self):
        super().__init__('data_collector_node')

        # === 核心配置参数 ===
        self.target_freq = 50.0  # <--- 修改为 50Hz (每秒采集50次)
        self.batch_size = 1000   # 每 1000 帧保存为一个文件
        self.save_dir = "collected_data"
        self.file_index = 1
        
        # 创建保存目录
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        # === 数据缓存区 ===
        self.buffer = {
            'cmd_vel': [],       
            'joint_pos': [],     
            'joint_vel': [],     
            'gyro_ang_vel': [],  
            'base_rot_mat': [],  
            'base_lin_acc': [],  
            'joint_commands': [] 
        }

        # === 临时变量 (Zero-Order Hold) ===
        # 用于存储最新收到的 Topic 数据
        self.latest_cmd_vel = np.zeros(3)
        self.latest_joint_pos = np.zeros(12)
        self.latest_joint_vel = np.zeros(12)
        self.latest_joint_cmd = np.zeros(12)
        
        # IMU 临时变量
        self.latest_gyro = np.zeros(3)
        self.latest_acc = np.zeros(3)
        self.latest_quat = [0.0, 0.0, 0.0, 1.0] # x, y, z, w
        
        # 就绪标志位
        self.data_ready = {
            'cmd_vel': False,
            'lower_body': False,
            'joint_cmd': False,
            'imu': False
        }

        # === 订阅者 ===
        # 请根据实际 Topic 名称确认是否需要修改
        self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        self.create_subscription(JointState, '/lower_body_state', self.lower_body_callback, 10)
        self.create_subscription(JointState, '/joint_cmd', self.joint_cmd_callback, 10)
        self.create_subscription(Imu, '/imu', self.imu_callback, 10)

        # === 定时器 (核心逻辑) ===
        # 周期 = 1.0 / 50.0 = 0.02秒
        timer_period = 1.0 / self.target_freq
        self.timer = self.create_timer(timer_period, self.timer_callback)

        self.get_logger().info(f"采集节点启动: 目标频率 {self.target_freq}Hz, 每组 {self.batch_size} 帧。")
        self.get_logger().info(f"数据将保存至: {os.path.abspath(self.save_dir)}")

    # --- 回调函数：仅更新最新状态 ---

    def cmd_vel_callback(self, msg):
        self.latest_cmd_vel = np.array([msg.linear.x, msg.linear.y, msg.angular.z])
        self.data_ready['cmd_vel'] = True

    def lower_body_callback(self, msg):
        # 注意：如果使用自定义消息，msg.position可能需要改为 msg.motor_state[i].q
        if hasattr(msg, 'position') and len(msg.position) >= 12:
            self.latest_joint_pos = np.array(msg.position[:12])
            self.latest_joint_vel = np.array(msg.velocity[:12])
        # 针对自定义消息的备用逻辑 (示例)
        # elif hasattr(msg, 'motor_state'):
        #     self.latest_joint_pos = np.array([m.q for m in msg.motor_state[:12]])
        #     self.latest_joint_vel = np.array([m.dq for m in msg.motor_state[:12]])
        
        self.data_ready['lower_body'] = True

    def joint_cmd_callback(self, msg):
        if hasattr(msg, 'position') and len(msg.position) >= 12:
            self.latest_joint_cmd = np.array(msg.position[:12])
        elif hasattr(msg, 'data') and len(msg.data) >= 12:
            self.latest_joint_cmd = np.array(msg.data[:12])
        
        self.data_ready['joint_cmd'] = True

    def imu_callback(self, msg):
        self.latest_gyro = np.array([msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z])
        self.latest_acc = np.array([msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z])
        self.latest_quat = [msg.orientation.x, msg.orientation.y, msg.orientation.z, msg.orientation.w]
        self.data_ready['imu'] = True

    # --- 定时器：以 50Hz 频率采样并保存 ---

    def timer_callback(self):
        # 1. 等待所有 Topic 至少收到过一次数据
        if not all(self.data_ready.values()):
            return

        # 2. 数据转换 (只在采样时刻计算，节省性能)
        try:
            rot_mat = R.from_quat(self.latest_quat).as_matrix() # (3, 3)
        except ValueError:
            # 防止四元数归一化错误导致崩溃，使用单位矩阵兜底
            rot_mat = np.eye(3)

        # 3. 存入缓存
        self.buffer['cmd_vel'].append(self.latest_cmd_vel)
        self.buffer['joint_pos'].append(self.latest_joint_pos)
        self.buffer['joint_vel'].append(self.latest_joint_vel)
        self.buffer['joint_commands'].append(self.latest_joint_cmd)
        self.buffer['gyro_ang_vel'].append(self.latest_gyro)
        self.buffer['base_lin_acc'].append(self.latest_acc)
        self.buffer['base_rot_mat'].append(rot_mat)

        # 4. 检查是否满足 Batch Size (1000)
        # 50Hz 下，存满 1000 条需要 20 秒
        if len(self.buffer['cmd_vel']) >= self.batch_size:
            self.save_buffer()

    def save_buffer(self):
        filename = f"{self.file_index}.npz"
        filepath = os.path.join(self.save_dir, filename)
        
        self.get_logger().info(f"正在保存 {filepath} ...")

        try:
            # 构造字典
            data_to_save = {
                'cmd_vel': np.array(self.buffer['cmd_vel']),           # (1000, 3)
                'joint_pos': np.array(self.buffer['joint_pos']),       # (1000, 12)
                'joint_vel': np.array(self.buffer['joint_vel']),       # (1000, 12)
                'gyro_ang_vel': np.array(self.buffer['gyro_ang_vel']), # (1000, 3)
                'base_rot_mat': np.array(self.buffer['base_rot_mat']), # (1000, 3, 3)
                'base_lin_acc': np.array(self.buffer['base_lin_acc']), # (1000, 3)
                'joint_commands': np.array(self.buffer['joint_commands']) # (1000, 12)
            }

            # 写入磁盘
            np.savez(filepath, **data_to_save)
            
            self.file_index += 1
            self.get_logger().info(f"保存成功 (索引: {self.file_index})")

        except Exception as e:
            self.get_logger().error(f"保存文件失败: {str(e)}")
        
        finally:
            # 清空缓存
            for key in self.buffer:
                self.buffer[key] = []

def main(args=None):
    rclpy.init(args=args)
    node = DataCollector()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()