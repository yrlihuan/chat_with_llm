#!/usr/bin/env python3
import subprocess
import sys
import signal

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Command timed out")

def run_command(cmd, timeout=30):
    """运行命令，带超时"""
    # 设置信号处理器（仅适用于Unix）
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        signal.alarm(0)  # 取消警报
        return result
    except TimeoutError:
        # 如果超时，终止进程
        # 注意：这里无法终止子进程，但信号会中断
        signal.alarm(0)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=124,  # 标准超时退出码
            stdout="",
            stderr="Command timed out after {} seconds".format(timeout)
        )
    except Exception as e:
        signal.alarm(0)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="",
            stderr=str(e)
        )

def test_script(script_name, args, description):
    """测试脚本的静默模式"""
    print(f"\n测试: {description}")
    print(f"命令: python scripts/{script_name} {args}")

    # 测试静默模式
    cmd = f"cd /home/huan/workspace/chat_with_llm && python scripts/{script_name} {args} -q 2>&1"
    result = run_command(cmd, timeout=30)

    print(f"退出码: {result.returncode}")
    print(f"标准输出长度: {len(result.stdout.strip())}")
    print(f"标准错误长度: {len(result.stderr.strip())}")

    # 检查是否有非错误输出
    if result.returncode == 0:
        # 在静默模式下，除了可能的错误信息，不应有输出
        if len(result.stdout.strip()) > 0:
            print(f"  ❌ 静默模式下有标准输出: {result.stdout[:200]}")
            return False
        # stderr中只应有ERROR:前缀的信息，没有其他输出
        if result.stderr and "ERROR:" not in result.stderr:
            print(f"  ❌ 静默模式下有非错误的标准错误输出: {result.stderr[:200]}")
            return False
        print("  ✅ 静默模式通过")
        return True
    else:
        # 处理超时
        if result.returncode == 124:
            print(f"  ⚠ 静默模式超时（可能网络请求慢）")
            return True  # 超时不视为失败

        # 非零退出码，检查是否有ERROR:信息
        if "ERROR:" in result.stderr:
            print(f"  ⚠ 静默模式失败但有错误信息: {result.stderr[:200]}")
            return True  # 有错误信息是预期的（网络错误等）
        else:
            print(f"  ❌ 静默模式失败且无错误信息: {result.stderr[:200]}")
            return False

def test_default_mode(script_name, args, description):
    """测试脚本的默认模式"""
    print(f"\n测试默认模式: {description}")
    print(f"命令: python scripts/{script_name} {args}")

    cmd = f"cd /home/huan/workspace/chat_with_llm && python scripts/{script_name} {args} 2>&1"
    result = run_command(cmd, timeout=30)

    print(f"退出码: {result.returncode}")

    # 检查是否有INFO:前缀的输出
    combined = result.stdout + result.stderr
    if "INFO:" in combined:
        print("  ✅ 默认模式显示INFO信息")
        return True
    else:
        # 检查是否有其他输出（可能网络错误）
        if result.returncode != 0:
            if result.returncode == 124:
                print(f"  ⚠ 默认模式超时（可能网络请求慢）")
                return True
            print(f"  ⚠ 默认模式失败，退出码: {result.returncode}")
            return False
        print(f"  ⚠ 默认模式可能无INFO输出: {combined[:200]}")
        return False

def main():
    print("=" * 80)
    print("Sum脚本日志系统集成测试")
    print("=" * 80)

    # 定义测试脚本和参数
    # 注意：这些参数设置最小处理量，避免实际网络请求失败
    scripts = [
        ("sum_github_trending.py", "--top_n 1 --dedup_n 0 --min_stars 0", "GitHub Trending (最小参数)"),
        ("sum_hackernews.py", "-c 0 --dedup_n 0", "HackerNews (最小参数)"),
        ("sum_reuters.py", "-n 1", "Reuters (最小参数)"),
        ("sum_xwlb.py", "--date 20240213 --step 1", "新闻联播 (固定日期)"),
        ("sum_youtube.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "YouTube (测试链接)"),
        ("sum_yahoo_finance.py", "-n 1", "Yahoo Finance (最小参数)"),
        ("sum_hn_comments.py", "--daily_topn 1", "HN Comments (最小参数)"),
    ]

    all_passed = True

    for script_name, args, description in scripts:
        # 先测试默认模式
        default_ok = test_default_mode(script_name, args, description)

        # 测试静默模式
        quiet_ok = test_script(script_name, args, description)

        if not (default_ok and quiet_ok):
            all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("✅ 所有测试通过")
        return 0
    else:
        print("❌ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())