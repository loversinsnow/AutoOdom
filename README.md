# AutoOdom 论文复现指南

## 🖥️ 系统要求

* **操作系统**: Ubuntu 22.04

## ⚙️ 软件下载与环境配置

1. **安装 Conda 环境**
建议安装 Anaconda 或 Miniconda 以便进行 Python 虚拟环境管理。
2. **安装 Isaac Sim 和 Isaac Lab**
请参考 [Isaac Lab 官方文档](https://isaac-sim.github.io/IsaacLab/main/source/setup/installation/pip_installation.html) 安装 Python 版本的 Isaac Sim 和 Isaac Lab（Python version = 3.11）。
3. **克隆 AutoOdom 仓库**
```bash
git clone https://github.com/DOGOGOD/AutoOdom.git
```



## 🚀 行走策略训练 (Locomotion Policy)

### 训练方法

```bash
cd ~/AutoOdom/robot_lab
conda activate <your_env_name>
python scripts/reinforcement_learning/rsl_rl/train.py --task=<TASK_NAME> --headless
```

> **💡 说明：**
> * **获取 TASK_NAME**：可通过运行 `/AutoOdom/robot_lab/scripts/tools/list_envs.py` 查看所有可用任务名称。
> * **无头模式**：`--headless` 参数表示以非可视化模式运行，推荐在长轮次训练中使用以提高效率。
> * **更多参数**：详细参数配置请查阅 `scripts/reinforcement_learning/rsl_rl/train.py` 源码。
>
> 

**关于日志与权重：**
训练生成的权重文件将默认保存在 `/home/dogogod/AutoOdom/robot_lab/logs` 路径下（请注意：此为原作者路径，实际运行请检查您的本地生成路径）。

### 关于 MagicBot Z1 机器人

对于 Magicbot Z1，通常使用官方的 Magic Lab。本仓库虽然提供了兼容 Isaac Sim 和 Isaac Lab 的 `magic_rl_lab` 仓库，但**不建议优先使用**（可能存在路径匹配报错问题）。

* 如需使用，请参考 `magic_rl_lab` 目录下的 `README.md` 安装依赖。
* **注意**：本项目已预先为您训练好了 **Booster T1 (robot_lab)** 和 **MagicBot Z1 (magic_rl_lab)** 的行走策略，您可以直接调用。

---

## 📂 仿真环境运动数据收集

### 以 Booster T1 机器人为例

**1. 手动运行收集程序**

```bash
conda activate <your_env_name>
python AutoOdom/robot_lab/BoosterT1AutoOdom/DataCollect.py
```

**2. 使用脚本自动批量收集**
您也可以使用 Runner 脚本来自动运行收集流程：

```bash
conda activate <your_env_name>
python AutoOdom/robot_lab/BoosterT1AutoOdom/Runner.py
```

> **注**：采集的数据文件将以 `.npz` 格式存储在 `BoosterT1AutoOdom` 目录下。

---

## 🧠 Stage 1 预训练

### 以 Booster T1 机器人为例

**1. 启动训练**

```bash
conda activate <your_env_name>
python AutoOdom/robot_lab/BoosterT1AutoOdom/Train.py
```

训练结束后，程序会在 `BoosterT1AutoOdom` 目录中生成训练曲线图。如果结果未达预期，您可以调整训练参数或修改模型结构。

**2. 可视化验证**
我们提供了可视化脚本，该程序将随机抽取 5 个数据文件，利用训练好的权重进行轨迹推理，并绘制真实轨迹与推理轨迹的对比图。

```bash
conda activate <your_env_name>
python AutoOdom/robot_lab/BoosterT1AutoOdom/Visualize.py
```

**3. 预训练模型**
仓库中已包含几个训练好的模型供测试。由于效果可能受多种因素影响，如不符合预期，建议调整参数重新训练。

> **MagicBot Z1 说明**：
> 本项目同样提供了 MagicBot Z1 的训练、收集程序及预训练权重，文件位于 `magic_rl_lab` 中。使用方法与 Booster T1 类似，建议参照上述流程进行配置。

---

## 🤖 真实运动数据收集

### 以 Booster T1 机器人为例

#### 1. 软件安装与环境配置

```bash
# 安装 SDK
cd AutoOdom/sdk_release
sudo ./install.sh
# 安装 ROS2
wget http://fishros.com/install -O fishros && . fishros 
# 安装 booster_ros2_interface
cd AutoOdom/booster_robotics_sdk_ros2/booster_ros2_interface
colcon build
```

#### 2. 收集运动数据

**步骤 A：连接机器人**
请通过有线方式连接 Booster T1 机器人，具体操作参考 [Booster T1 官方说明书](https://booster.feishu.cn/wiki/H2Dowdnokij7p8ks9K3cZPuJnOg)。

**步骤 B：运行收集程序**

```bash
source /opt/ros/<distro>/setup.bash
source booster_robotics_sdk_ros2/install/setup.bash
python3 booster_robotics_sdk_ros2/booster_ros2_example/low_level/scripts/data_collector.py
```

> 数据存储位置：`AutoOdom/booster_robotics_sdk_ros2/data_output`

#### 3. Stage 1 模型初步检验

**步骤 A：准备数据**
将上一步收集到的真实数据复制到 `AutoOdom/robot_lab/RealData` 目录中。

**步骤 B：运行检验程序**

```bash
conda activate <your_env_name>
python AutoOdom/robot_lab/BoosterT1AutoOdom/Stage1Check.py
```

推理生成的轨迹对比图将保存在 `AutoOdom/robot_lab/BoosterT1AutoOdom` 文件夹中。
