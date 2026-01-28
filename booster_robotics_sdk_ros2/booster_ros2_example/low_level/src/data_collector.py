#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from booster_interface.msg import LowState, LowCmd
from geometry_msgs.msg import Twist
import numpy as np
import os
import glob
import math
from threading import Lock


def rpy_to_rotmat(rpy):
    roll, pitch, yaw = rpy
    cr = math.cos(roll)
    sr = math.sin(roll)
    cp = math.cos(pitch)
    sp = math.sin(pitch)
    cy = math.cos(yaw)
    sy = math.sin(yaw)
    # R = Rz(yaw) * Ry(pitch) * Rx(roll)
    R = np.array([
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp, cp * sr, cp * cr]
    ], dtype=np.float32)
    return R


class DataCollector(Node):
    def __init__(self, out_dir='data_output', sample_hz=50, batch=1000):
        super().__init__('data_collector')
        self.declare_parameter('output_dir', out_dir)
        self.output_dir = self.get_parameter('output_dir').value
        os.makedirs(self.output_dir, exist_ok=True)

        self.sample_hz = sample_hz
        self.batch = batch
        self.interval = 1.0 / float(self.sample_hz)

        # latest messages
        self._lock = Lock()
        self.latest_low_state = None
        self.latest_low_cmd = None
        self.latest_cmd_vel = None

        # buffers
        self.cmd_vel_buf = []  # (3,)
        self.joint_pos_buf = []  # (23,)
        self.joint_vel_buf = []  # (23,)
        self.joint_cmd_buf = []  # (23,)
        self.gyro_buf = []  # (3,)
        self.rotmat_buf = []  # (3,3)
        self.imu_acc_buf = []  # (3,)

        # subscriptions
        self.create_subscription(LowState, '/low_state', self.low_state_cb, 10)
        # LowCmd often published by examples on 'test_control'
        self.create_subscription(LowCmd, 'test_control', self.low_cmd_cb, 10)
        self.create_subscription(LowCmd, '/low_cmd', self.low_cmd_cb, 10)
        self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_cb, 10)

        # timer for sampling
        self.create_timer(self.interval, self.timer_cb)

        self.get_logger().info('DataCollector started: %d Hz, batch %d' % (self.sample_hz, self.batch))

    def low_state_cb(self, msg: LowState):
        with self._lock:
            self.latest_low_state = msg

    def low_cmd_cb(self, msg: LowCmd):
        with self._lock:
            self.latest_low_cmd = msg

    def cmd_vel_cb(self, msg: Twist):
        with self._lock:
            self.latest_cmd_vel = msg

    def safe_get_joints_from_lowstate(self, low_state, expect=23):
        # combine parallel + serial
        q_list = []
        dq_list = []
        if low_state is None:
            return np.zeros(expect, dtype=np.float32), np.zeros(expect, dtype=np.float32)
        for m in low_state.motor_state_parallel:
            q_list.append(m.q)
            dq_list.append(m.dq)
        for m in low_state.motor_state_serial:
            q_list.append(m.q)
            dq_list.append(m.dq)
        # pad or trim to expect
        q_arr = np.zeros(expect, dtype=np.float32)
        dq_arr = np.zeros(expect, dtype=np.float32)
        n = min(expect, len(q_list))
        if n > 0:
            q_arr[:n] = np.array(q_list[:n], dtype=np.float32)
            dq_arr[:n] = np.array(dq_list[:n], dtype=np.float32)
        return q_arr, dq_arr

    def safe_get_cmds_from_lowcmd(self, low_cmd, expect=23):
        q_list = []
        if low_cmd is None:
            return np.zeros(expect, dtype=np.float32)
        for m in low_cmd.motor_cmd:
            q_list.append(m.q)
        arr = np.zeros(expect, dtype=np.float32)
        n = min(expect, len(q_list))
        if n > 0:
            arr[:n] = np.array(q_list[:n], dtype=np.float32)
        return arr

    def timer_cb(self):
        # sample latests
        with self._lock:
            ls = self.latest_low_state
            lc = self.latest_low_cmd
            cv = self.latest_cmd_vel

        # cmd_vel: linear x,y,z
        if cv is None:
            cmd_vel = np.zeros(3, dtype=np.float32)
        else:
            cmd_vel = np.array([cv.linear.x, cv.linear.y, cv.linear.z], dtype=np.float32)

        # joint pos/vel
        joint_pos, joint_vel = self.safe_get_joints_from_lowstate(ls, expect=23)

        # joint commands
        joint_cmd = self.safe_get_cmds_from_lowcmd(lc, expect=23)

        # imu
        if ls is None or ls.imu_state is None:
            gyro = np.zeros(3, dtype=np.float32)
            rotmat = np.eye(3, dtype=np.float32)
            acc = np.zeros(3, dtype=np.float32)
        else:
            gyro = np.array(list(ls.imu_state.gyro), dtype=np.float32)
            rpy = list(ls.imu_state.rpy)
            rotmat = rpy_to_rotmat(rpy)
            acc = np.array(list(ls.imu_state.acc), dtype=np.float32)

        # append to buffers
        self.cmd_vel_buf.append(cmd_vel)
        self.joint_pos_buf.append(joint_pos)
        self.joint_vel_buf.append(joint_vel)
        self.joint_cmd_buf.append(joint_cmd)
        self.gyro_buf.append(gyro)
        self.rotmat_buf.append(rotmat)
        self.imu_acc_buf.append(acc)

        # when reach batch, save
        if len(self.cmd_vel_buf) >= self.batch:
            self.get_logger().info('Batch full, saving to disk...')
            self.save_batch_and_pack()
            # clear buffers
            self.cmd_vel_buf.clear()
            self.joint_pos_buf.clear()
            self.joint_vel_buf.clear()
            self.joint_cmd_buf.clear()
            self.gyro_buf.clear()
            self.rotmat_buf.clear()
            self.imu_acc_buf.clear()

    def next_index(self):
        files = glob.glob(os.path.join(self.output_dir, '*.npz'))
        if not files:
            return 1
        nums = []
        for f in files:
            base = os.path.basename(f)
            name, _ = os.path.splitext(base)
            try:
                nums.append(int(name))
            except Exception:
                continue
        if not nums:
            return 1
        return max(nums) + 1

    def save_batch_and_pack(self):
        idx = self.next_index()
        # prepare arrays
        cmd_vel_arr = np.stack(self.cmd_vel_buf, axis=0).astype(np.float32)  # (batch,3)
        joint_pos_arr = np.stack(self.joint_pos_buf, axis=0).astype(np.float32)  # (batch,23)
        joint_vel_arr = np.stack(self.joint_vel_buf, axis=0).astype(np.float32)
        joint_cmd_arr = np.stack(self.joint_cmd_buf, axis=0).astype(np.float32)
        gyro_arr = np.stack(self.gyro_buf, axis=0).astype(np.float32)
        rotmat_arr = np.stack(self.rotmat_buf, axis=0).astype(np.float32)  # (batch,3,3)
        imu_acc_arr = np.stack(self.imu_acc_buf, axis=0).astype(np.float32)

        # save individual .npy files with prefix index_ (as required: store as .npy)
        prefix = os.path.join(self.output_dir, f'{idx}_')
        np.save(prefix + 'cmd_vel.npy', cmd_vel_arr)
        np.save(prefix + 'joint_pos.npy', joint_pos_arr)
        np.save(prefix + 'joint_vel.npy', joint_vel_arr)
        np.save(prefix + 'joint_commands.npy', joint_cmd_arr)
        np.save(prefix + 'gyro_ang_vel.npy', gyro_arr)
        np.save(prefix + 'base_rot_mat.npy', rotmat_arr)
        np.save(prefix + 'imu_lin_acc.npy', imu_acc_arr)

        # pack all into an npz named by index (e.g., 1.npz)
        npz_path = os.path.join(self.output_dir, f'{idx}.npz')
        np.savez_compressed(npz_path,
                            cmd_vel=cmd_vel_arr,
                            joint_pos=joint_pos_arr,
                            joint_vel=joint_vel_arr,
                            joint_commands=joint_cmd_arr,
                            gyro_ang_vel=gyro_arr,
                            base_rot_mat=rotmat_arr,
                            imu_lin_acc=imu_acc_arr)

        # remove individual .npy files after successful packing, keep only the .npz
        try:
            npy_files = [
                prefix + 'cmd_vel.npy',
                prefix + 'joint_pos.npy',
                prefix + 'joint_vel.npy',
                prefix + 'joint_commands.npy',
                prefix + 'gyro_ang_vel.npy',
                prefix + 'base_rot_mat.npy',
                prefix + 'imu_lin_acc.npy',
            ]
            for p in npy_files:
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception as e:
                    self.get_logger().warn(f'Failed to remove {p}: {e}')
        except Exception:
            # defensive: ignore deletion errors
            pass

        self.get_logger().info(f'Saved batch {idx} -> {npz_path} (individual .npy removed)')


def main(args=None):
    rclpy.init(args=args)
    node = DataCollector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
