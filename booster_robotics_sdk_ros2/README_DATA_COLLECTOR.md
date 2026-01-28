Data Collector for robot motion

Dependencies:
- ROS2 (rclpy)
- numpy

Run:

```bash
# source ROS2 and workspace
source /opt/ros/<distro>/setup.bash
source /home/dogogod/booster_robotics_sdk_ros2/install/setup.bash
python3 /home/dogogod/booster_robotics_sdk_ros2/booster_ros2_example/low_level/scripts/data_collector.py

# Or make the script executable and run directly:
chmod +x /home/dogogod/booster_robotics_sdk_ros2/booster_ros2_example/low_level/scripts/data_collector.py
./booster_ros2_example/low_level/scripts/data_collector.py
```

Output:
- Files saved under `data_output` (default) in workspace.
- Each batch of 1000 samples produces individual .npy files with prefix `<index>_` and a packed `<index>.npz`.
- Arrays inside .npz use keys: `cmd_vel`, `joint_pos`, `joint_vel`, `joint_commands`, `gyro_ang_vel`, `base_rot_mat`, `imu_lin_acc`.
