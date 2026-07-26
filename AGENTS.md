# Repository Guidelines

## Project Structure & Module Organization

`robot_lab/go2_autoodom/` is the maintained Unitree Go2 workflow: Isaac Lab task registration, policy tools, two-stage odometry, real control, and tests. `robot_lab/source/robot_lab/robot_lab/` contains the broader Isaac Lab extension. The legacy Booster workflow remains in `robot_lab/BoosterT1AudoOdom/` (retain this spelling). `magiclab_rl_lab/`, `sdk_release/`, and `booster_robotics_sdk_ros2/` are legacy robot-specific components.

Treat `logs/`, `outputs/`, ROS `build/` and `install/`, `data_output/`, plots, checkpoints, and generated `.npz` files as artifacts. Add large artifacts only when they are intentional reproduction fixtures.

## Build, Test, and Development Commands

- `conda activate prio-tracking` selects the required Python 3.10, Isaac Sim 4.5, and Isaac Lab 2.1 environment; do not alter it from repository scripts.
- `cd robot_lab && python -m go2_autoodom.train_policy --headless --device cuda:0` trains and exports the Go2 control policy under `logs/autoodom_sim/<timestamp>/`.
- `cd robot_lab && python -m go2_autoodom.train_stage1 --data '<run>/data/sim/*.npz' --run-dir '<run>'` writes simulation Stage 1 under the same run’s `odometry/`.
- `cd robot_lab && python -m go2_autoodom.train_stage2 --help` documents real-data Stage 2 arguments.
- `cmake -S sdk_release -B sdk_release/build && cmake --build sdk_release/build -j` builds SDK examples.
- `cd booster_robotics_sdk_ros2 && colcon build` builds the ROS 2 packages; source `install/setup.bash` before running nodes.

## Coding Style & Naming Conventions

Use four-space indentation. Python follows `robot_lab/pyproject.toml`: Black-compatible Ruff formatting, double quotes, and a 120-character line limit. Run `cd robot_lab && python -m ruff check source scripts go2_autoodom` and `python -m ruff format --check source scripts go2_autoodom`. Use `snake_case` for modules/functions and `PascalCase` for classes. Format ROS C++ with the nearest `.clang-format`.

## Testing Guidelines

Run `cd robot_lab && PYTHONPATH=. python -m unittest discover -s go2_autoodom/tests -v`. Tests must cover data shapes/order, Stage 1→2 transfer, autoregressive leakage, mocap geometry, DDS mapping, and safety behavior. Isaac smoke tests require a GPU; real-control tests must remain dry-run and must never publish to `rt/lowcmd`.

## Commit & Pull Request Guidelines

Recent history uses short imperative subjects such as `Update README.md`. Keep commits focused. Pull requests must state the tested environment, robot/task, commands, data/checkpoint impact, and whether hardware validation was dry-run or live. Link issues and include relevant curves. Never commit credentials, robot network details, large recordings, or developer-specific absolute paths. Go2 code must not import or read from `proprio_sim2real_new`.
