import subprocess
import sys
import time
import os

def run_batch_tasks():
    # 配置参数
    target_script = "Headless.py"  # 目标脚本名称
    total_runs = 200               # 总运行次数
    cooldown_seconds = 5           # 每次运行后的冷却时间(秒)，防止显存未释放

    # 检查目标文件是否存在
    if not os.path.exists(target_script):
        print(f"[Error] 找不到文件: {target_script}")
        print("请将此脚本放在与 AutoOdom.py 同一目录下。")
        return

    print(f"=== 开始批量运行任务: 目标 {total_runs} 次 ===")

    try:
        for i in range(total_runs):
            current_run = i + 1
            print(f"\n[Batch] 正在启动第 {current_run}/{total_runs} 次运行...")
            
            start_time = time.time()

            # 使用 subprocess.run 启动子进程
            # sys.executable 确保使用当前环境的 Python 解释器
            # 如果 AutoOdom.py 需要参数，可以在列表中添加，例如:
            # [sys.executable, target_script, "--device", "cuda:0"]
            process = subprocess.run([sys.executable, target_script])

            end_time = time.time()
            duration = end_time - start_time

            # 检查运行结果
            if process.returncode == 0:
                print(f"[Batch] 第 {current_run} 次运行成功 (耗时: {duration:.2f}s)")
            else:
                print(f"[Warning] 第 {current_run} 次运行返回错误代码: {process.returncode}")

            # 冷却等待 (对 Isaac Sim 很重要)
            if current_run < total_runs:
                print(f"[Batch] 等待 {cooldown_seconds} 秒释放资源...")
                time.sleep(cooldown_seconds)

    except KeyboardInterrupt:
        print("\n\n[Batch] 检测到用户中断 (Ctrl+C)，停止批量运行。")
    except Exception as e:
        print(f"\n[Error] 发生意外错误: {e}")

    print("=== 批量任务结束 ===")

if __name__ == "__main__":
    run_batch_tasks()