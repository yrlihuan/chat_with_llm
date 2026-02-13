"""
统一日志工具，用于控制sum_xx脚本的输出
默认显示所有信息，-q/--quiet模式下只显示错误
"""

import sys
from typing import Any

class SumLogger:
    """
    统一的日志记录器，支持两种模式：
    - 默认模式：显示所有信息
    - 静默模式（-q）：只显示错误信息
    """
    def __init__(self, quiet: bool = False) -> None:
        self.quiet = quiet

    def _format_message(self, msg: str, args: tuple) -> str:
        """格式化消息，支持两种格式：{} 和 %

        智能检测使用哪种格式化方式：
        1. 如果没有参数，直接返回原消息
        2. 如果消息包含{}，使用str.format()
        3. 否则，使用%格式化（向后兼容）
        """
        if not args:
            return msg

        # 检查消息是否包含{}占位符
        if '{}' in msg or '{' in msg:
            try:
                return msg.format(*args)
            except (IndexError, KeyError, ValueError) as e:
                # 如果format失败，尝试使用%格式化
                try:
                    return msg % args
                except (TypeError, ValueError):
                    # 如果两种方式都失败，返回原始消息和参数
                    return f"{msg} [格式化失败: {e}, 参数: {args}]"
        else:
            # 使用%格式化（向后兼容）
            try:
                return msg % args
            except (TypeError, ValueError) as e:
                # 如果%格式化失败，尝试使用str.format()
                try:
                    # 将消息转换为{}格式
                    formatted_msg = msg.replace('%s', '{}').replace('%d', '{}').replace('%f', '{}')
                    return formatted_msg.format(*args)
                except (IndexError, KeyError, ValueError):
                    # 如果两种方式都失败，返回原始消息和参数
                    return f"{msg} [格式化失败: {e}, 参数: {args}]"

    def error(self, msg: str, *args: Any) -> None:
        """错误信息：总是显示到stderr"""
        formatted_msg = self._format_message(msg, args)
        print(f"ERROR: {formatted_msg}", file=sys.stderr)

    def result(self, msg: str) -> None:
        """最终结果：非静默模式时显示"""
        if not self.quiet:
            print(msg)

    def info(self, msg: str, *args: Any) -> None:
        """进度/统计信息：非静默模式时显示"""
        if not self.quiet:
            formatted_msg = self._format_message(msg, args)
            print(f"INFO: {formatted_msg}")

    def is_quiet(self) -> bool:
        """检查是否为静默模式（用于控制tqdm等）"""
        return self.quiet