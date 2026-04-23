# AutoOdom Paper Reproduction

## 🖥️ System Requirements

* **Operating System**: Ubuntu 22.04

## ⚙️ Software & Environment Setup

1. **Install Conda**
   It is recommended to install Anaconda or Miniconda for Python virtual environment management.

2. **Install Isaac Sim and Isaac Lab**
   Follow the [Isaac Lab official documentation](https://isaac-sim.github.io/IsaacLab/main/source/setup/installation/pip_installation.html) to install the Python version of Isaac Sim and Isaac Lab (Python version = 3.11).

3. **Clone the AutoOdom Repository**
   ```bash
   git clone https://github.com/DOGOGOD/AutoOdom.git
   ```

---

## 🚀 Locomotion Policy Training

### Training

```bash
cd ~/AutoOdom/robot_lab
conda activate <your_env_name>
python scripts/reinforcement_learning/rsl_rl/train.py --task=<TASK_NAME> --headless
```

> **💡 Notes:**
> * **Getting TASK_NAME**: Run `/AutoOdom/robot_lab/scripts/tools/list_envs.py` to view all available task names.
> * **Headless mode**: The `--headless` flag runs training without visualization. Recommended for long training runs to improve efficiency.
> * **More options**: See `scripts/reinforcement_learning/rsl_rl/train.py` for detailed parameter configuration.

**Logs & Weights:**
Trained weight files are saved by default to `/home/dogogod/AutoOdom/robot_lab/logs` (note: this is the original author's path — please verify the actual output path on your local machine).

### About the MagicBot Z1 Robot

For MagicBot Z1, the official Magic Lab is typically used. Although this repository provides a `magic_rl_lab` repo compatible with Isaac Sim and Isaac Lab, **it is not the recommended first choice** (path-matching errors may occur).

* If you choose to use it, refer to the `README.md` inside the `magic_rl_lab` directory to install dependencies.
* **Note**: Pre-trained locomotion policies for both **Booster T1 (robot_lab)** and **MagicBot Z1 (magic_rl_lab)** are already included — you can use them directly.

---

## 📂 Simulation Motion Data Collection

### Example: Booster T1 Robot

**1. Manual Data Collection**

```bash
conda activate <your_env_name>
python AutoOdom/robot_lab/BoosterT1AutoOdom/DataCollect.py
```

**2. Automated Batch Collection via Runner Script**

```bash
conda activate <your_env_name>
python AutoOdom/robot_lab/BoosterT1AutoOdom/Runner.py
```

> **Note**: Collected data files are stored in `.npz` format under the `BoosterT1AutoOdom` directory.

---

## 🧠 Stage 1 Pre-Training

### Example: Booster T1 Robot

**1. Start Training**

```bash
conda activate <your_env_name>
python AutoOdom/robot_lab/BoosterT1AutoOdom/Train.py
```

After training, the program generates a training curve plot in the `BoosterT1AutoOdom` directory. If results are unsatisfactory, adjust training parameters or modify the model architecture.

**2. Visualization & Validation**
A visualization script is provided. It randomly selects 5 data files, runs trajectory inference using the trained weights, and plots a comparison between ground-truth and inferred trajectories.

```bash
conda activate <your_env_name>
python AutoOdom/robot_lab/BoosterT1AutoOdom/Visualize.py
```

**3. Pre-Trained Models**
Several pre-trained models are included in the repository for testing. Since performance may vary depending on multiple factors, re-training with adjusted parameters is recommended if results are not satisfactory.

> **MagicBot Z1 Note**:
> Training scripts, data collection programs, and pre-trained weights for MagicBot Z1 are also provided, located under `magic_rl_lab`. Usage is similar to Booster T1 — refer to the workflow above.

---

## 🤖 Real-World Motion Data Collection

### Example: Booster T1 Robot

#### 1. Software Installation & Environment Setup

```bash
# Install SDK
cd AutoOdom/sdk_release
sudo ./install.sh

# Install ROS2
wget http://fishros.com/install -O fishros && . fishros

# Install booster_ros2_interface
cd AutoOdom/booster_robotics_sdk_ros2/booster_ros2_interface
colcon build
```

#### 2. Collect Motion Data

**Step A: Connect the Robot**
Connect to the Booster T1 robot via a wired connection. Refer to the [Booster T1 official manual](https://booster.feishu.cn/wiki/H2Dowdnokij7p8ks9K3cZPuJnOg) for detailed instructions.

**Step B: Run the Data Collection Program**

```bash
source /opt/ros/<distro>/setup.bash
source booster_robotics_sdk_ros2/install/setup.bash
python3 booster_robotics_sdk_ros2/booster_ros2_example/low_level/scripts/data_collector.py
```

> Data output location: `AutoOdom/booster_robotics_sdk_ros2/data_output`

#### 3. Stage 1 Model Preliminary Validation

**Step A: Prepare Data**
Copy the real-world data collected in the previous step to the `AutoOdom/robot_lab/RealData` directory.

**Step B: Run the Validation Program**

```bash
conda activate <your_env_name>
python AutoOdom/robot_lab/BoosterT1AutoOdom/Stage1Check.py
```

The inferred trajectory comparison plots will be saved to the `AutoOdom/robot_lab/BoosterT1AutoOdom` folder.

---

## 🏗️ Future Goals

* [ ] Collect a sufficient volume of data samples
* [ ] Apply autoregressive training on real-world motion data
* [ ] Tune model training parameters to improve generalization and inference accuracy


# AutoOdom 论文复现

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

---

## 🏗️ 后续目标
* [ ] 收集足够样本量的数据  
* [ ] 对真实环境运动数据展开自回归训练  
* [ ] 调整模型训练参数，提升模型的泛化能力和推理准确度  
