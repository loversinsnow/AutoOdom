# AutoOdom on Unitree Go2

This repository reproduces AutoOdom on Unitree Go2 while preserving the existing Booster T1 implementation. The Go2 workflow lives in `robot_lab/go2_autoodom/` and does not import code, configuration, assets, or weights from `proprio_sim2real_new`.

## Fixed environment

The implementation targets the existing environment and does not install, upgrade, or downgrade it:

| Component | Version |
| --- | --- |
| Conda environment | `prio-tracking` |
| Python | 3.10.20 |
| Isaac Sim | 4.5.0 |
| Isaac Lab | 2.1.0 |
| RSL-RL | 2.3.1 |

Activate it before every command:

```bash
conda activate prio-tracking
cd /path/to/AutoOdom/robot_lab
python -m go2_autoodom.check_environment
```

Isaac Sim policy training and simulation collection require a working NVIDIA GPU. Stage 1, Stage 2, evaluation, and unit tests can run on CPU.

## Workflow

### 1. Train and export the Go2 locomotion policy

The task `AutoOdom-Isaac-Velocity-Flat-Unitree-Go2-v0` removes privileged base linear velocity, uses the canonical 12-joint deployment order, runs at 50 Hz, and applies action scales `0.125` to hips and `0.25` to thigh/calf joints.

```bash
python -m go2_autoodom.train_policy \
  --headless --device cuda:0 --num-envs 4096 --max-iterations 1500
```

This creates `logs/autoodom_sim/<SIM_RUN>/`, where `<SIM_RUN>` is a timestamp. RSL-RL checkpoints retain the reference layout (`model_<iteration>.pt`), and training automatically exports the deployable control model as `exported/policy.pt` with `exported/deployment.json`. To re-export an existing checkpoint:

```bash
python -m go2_autoodom.export_policy \
  --headless --device cuda:0 \
  --checkpoint logs/autoodom_sim/<SIM_RUN>/model_1499.pt
```

Do not use a policy exported from a task with a different observation or joint order.

### 2. Collect simulation data and train Stage 1

```bash
python -m go2_autoodom.collect_sim \
  --headless --device cuda:0 \
  --run-dir logs/autoodom_sim/<SIM_RUN> \
  --num-trajectories 10 --steps 10000

python -m go2_autoodom.train_stage1 \
  --data 'logs/autoodom_sim/<SIM_RUN>/data/sim/*.npz' \
  --run-dir logs/autoodom_sim/<SIM_RUN>
```

To continue an interrupted Stage 1 run, keep `--epochs` as the desired total epoch count. `--resume` without a path
loads `odometry/auto_odom_stage1_sim_last.pth` from the selected run:

```bash
python -m go2_autoodom.train_stage1 \
  --data 'logs/autoodom_sim/<SIM_RUN>/data/sim/*.npz' \
  --run-dir logs/autoodom_sim/<SIM_RUN> \
  --epochs 100 --workers 8 --device cuda:0 --resume
```

Stage 1 preserves the repository’s TCN, three-dimensional displacement output, combined loss, 50-frame history, normalization, and recursive evaluation behavior. Its input changes only from Booster’s 23 joints to Go2’s 12 joints (45 channels total).

The best simulation-trained odometry network is saved as:

```text
logs/autoodom_sim/<SIM_RUN>/odometry/auto_odom_stage1_sim_best.pth
```

`--steps` is the number of 50 Hz samples in each file. The collector resets between files and discards interrupted
fragments instead of joining simulation resets into one trajectory. At least three continuous trajectory files are
required so train, validation, and test data remain file-disjoint; ten files give a more useful split.

### 3. Collect real Go2 + mocap data

The Unitree SDK is loaded directly from the sibling directory `../unitree_sdk2_python` by default; it is not installed into Conda. ROS 2 must expose:

- `/Tracker0_Marker1/pose` through `/Tracker0_Marker8/pose`
- `/Tracker0/twist`

Dry-run still reads the real robot and mocap but publishes to a randomized isolated DDS topic:

```bash
python -m go2_autoodom.run_real \
  --deployment logs/autoodom_sim/<SIM_RUN>/exported/deployment.json \
  --output-dir /tmp/go2_autoodom_dryrun \
  --duration 60 --remote-command
```

Only after verifying dry-run, use live low-level control:

```bash
python -m go2_autoodom.run_real \
  --deployment logs/autoodom_sim/<SIM_RUN>/exported/deployment.json \
  --duration 60 --remote-command \
  --live --network-interface eno1
```

The live command creates `logs/autoodom_real/<REAL_RUN>/`, copies the exact control bundle used on the robot to `exported/policy.pt`, and saves synchronized trajectories under `data/real/`. The printed `<REAL_RUN>` path can be reused with `--run-dir` for additional trajectories.

Live mode disables Sport Mode, ramps to the default stand, and waits for an R1 edge before policy control. R2 or L2 immediately disables motors. Stale LowState/mocap, non-finite policy output, control discontinuities, joint-limit violations, and exceptions stop the run. Keep the robot suspended and the emergency stop reachable during first validation.

Real files contain synchronized joint state/action, gyro, IMU acceleration, IMU rotation, mocap rotation/position, command, and mocap-derived local displacement. Mocap is a training label and evaluation reference only; it is never an AutoOdom inference input.

### 4. Train paper Stage 2

Stage 2 gives real data a direct training role:

```bash
python -m go2_autoodom.train_stage2 \
  --data 'logs/autoodom_real/<REAL_RUN>/data/real/*.npz' \
  --stage1-checkpoint \
    logs/autoodom_sim/<SIM_RUN>/odometry/auto_odom_stage1_sim_best.pth \
  --run-dir logs/autoodom_real/<REAL_RUN>
```

It appends three IMU acceleration channels (45 → 48), copies all Stage 1 parameters, and initializes only the new first-layer columns to zero. Training is chronological and feeds back detached model predictions—never ground-truth displacement. Stage 1 remains read-only; Stage 2 writes `odometry/auto_odom_stage2_real_best.pth`, carrying the parent SHA-256 and train-only acceleration statistics.

Stage 2 fine-tunes the odometry network with real Go2/mocap data. It does not retrain the locomotion controller; the copied `exported/policy.pt` records exactly which control policy generated the real trajectories.

### Run-directory layout

Control-policy naming follows `proprio_sim2real_new`, while odometry files remain unambiguous:

```text
logs/autoodom_sim/<SIM_RUN>/
├── model_1499.pt
├── params/
├── exported/policy.pt
├── exported/deployment.json
├── data/sim/
└── odometry/auto_odom_stage1_sim_{best,last}.pth

logs/autoodom_real/<REAL_RUN>/
├── exported/policy.pt
├── exported/deployment.json
├── data/real/
└── odometry/auto_odom_stage2_real_{best,last}.pth
```

Each directory also contains `run_manifest.json`, which records the Stage/domain and keeps control-policy and odometry roles separate. No runtime code imports or reads `proprio_sim2real_new`.

### 5. Run the fixed 100-command evaluation

Simulation evaluation uses the repository-local Go2 MuJoCo model, the exported locomotion policy, and the Stage 1 best checkpoint:

```bash
python -m go2_autoodom.eval_mujoco
python -m go2_autoodom.eval_mujoco --load_run <SIM_RUN> --viewer --realtime
```

Without `--load_run`, the evaluator selects the latest complete timestamp under `logs/autoodom_sim/`. A timestamp or full run path is accepted. The real evaluator applies the same rule under `logs/autoodom_real/` and loads Stage 2:

```bash
# Safe interface/mocap check: publishes only to an isolated DDS topic.
python -m go2_autoodom.eval_real \
  --load_run <REAL_RUN> --command-start 2 --command-count 1

# Hardware evaluation after the dry-run check.
python -m go2_autoodom.eval_real \
  --load_run <REAL_RUN> --live --network-interface eno1
```

Real live mode disables Sport Mode, performs the stand ramp, and requires one R1 edge before the automatic sequence. Keep R2/L2 reachable throughout the run.

Both scripts use the fixed local copy of `eval_command.txt` (100 commands, checksum-verified). The first two columns define `[forward, left]` displacement in a frame created at the current true pose; average and final speed default to `0.8`. Commands with negative lateral displacement use the calibrated second return origin. There is no warm start.

AutoOdom estimated position is the only navigation feedback. MuJoCo position or mocap is used only for the `< 0.3 m` success test, metrics, and policy-driven return between commands; heading is not part of command success. Timeout is `||command|| / 0.8 × 1.01`. Results and per-command traces are written to `logs/autoodom_{sim,real}_eval/<timestamp>/`, including success rate, total commanded distance, true path length, and odometry endpoint error.

### 6. Compare both odometry stages offline

```bash
python -m go2_autoodom.evaluate \
  --data 'logs/autoodom_real/<REAL_RUN>/data/real/*.npz' \
  --split-json logs/autoodom_real/<REAL_RUN>/odometry/split.json --split test \
  --stage1-checkpoint \
    logs/autoodom_sim/<SIM_RUN>/odometry/auto_odom_stage1_sim_best.pth \
  --stage2-checkpoint \
    logs/autoodom_real/<REAL_RUN>/odometry/auto_odom_stage2_real_best.pth \
  --output logs/autoodom_real/<REAL_RUN>/evaluation.json
```

The report includes step RMSE, translational RPE, origin-aligned ATE, rigid Umeyama-aligned ATE, final drift, and relative final drift.

## Data contract

Every `.npz` trajectory is 50 Hz and uses the fixed order:

```text
FL/FR/RL/RR hip, FL/FR/RL/RR thigh, FL/FR/RL/RR calf
```

Required arrays are `joint_pos`, `joint_vel`, `joint_commands`, `gyro_ang_vel`, `imu_lin_acc`, `base_rot_mat`, `cmd_vel`, `pos_increment_hist`, and `root_pos_abs`. Loaders validate shapes, finite values, rate, source, and `joint_names`; legacy 23-DOF Booster files are rejected rather than silently mixed.

## Tests

```bash
PYTHONPATH=. python -m unittest discover -s go2_autoodom/tests -v
```

The suite covers data validation, joint/DDS mapping, 45/48-channel contracts, zero-padded Stage 2 transfer, absence of ground-truth feedback, command/frame/timeout semantics, latest-run resolution, local MuJoCo compilation, mocap reconstruction, remote decoding, safety clipping, and trajectory metrics. Hardware, full 100-command mocap evaluation, and long-running PPO validation must be performed on the connected Go2/GPU system.
