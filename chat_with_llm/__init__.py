from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("chat_with_llm")
except PackageNotFoundError:
    # package is not installed
    __version__ = "unknown"

# 导出logutils模块
from chat_with_llm import logutils