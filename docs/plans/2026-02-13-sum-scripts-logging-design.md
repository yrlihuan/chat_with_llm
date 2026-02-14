# Sum脚本统一日志系统设计

**日期**: 2026-02-13
**状态**: 已批准
**作者**: Claude Code
**相关需求**: 为所有sum_xx.py脚本添加统一的日志/静默模式控制，支持计划任务运行时避免不必要的输出

## 1. 概述

### 1.1 项目背景
`chat_with_llm`项目包含7个以`sum_`开头的Python脚本，用于自动化内容总结和信息处理：
- `sum_hackernews.py` - 总结HackerNews每日文章
- `sum_reuters.py` - 总结路透社财经新闻
- `sum_xwlb.py` - 分析新闻联播内容
- `sum_youtube.py` - 总结YouTube视频字幕
- `sum_yahoo_finance.py` - 总结雅虎财经新闻
- `sum_hn_comments.py` - 总结HackerNews评论
- `sum_github_trending.py` - 总结GitHub热门项目

这些脚本目前都直接使用`print()`语句输出进度、统计、错误和结果信息。当作为计划任务（cron）运行时，正常输出会触发邮件通知，造成不必要的干扰。

### 1.2 设计目标
- **统一日志控制**：为所有sum_xx脚本提供一致的日志输出控制
- **简化模式**：默认显示所有信息，`-q/--quiet`模式下只显示错误信息
- **计划任务友好**：静默模式下只有错误会触发邮件通知，正常运行时无干扰
- **向后兼容**：默认行为与现有脚本保持一致
- **易于维护**：集中管理日志逻辑，减少代码重复

## 2. 功能需求

### 2.1 输出模式
1. **默认模式**（不带参数）
   - 显示所有进度信息（如"Fetching..."、"Found X items"）
   - 显示统计信息（如"Processing X projects"）
   - 显示最终结果（LLM生成的总结内容）
   - 显示错误信息（到stderr）

2. **静默模式**（`-q`或`--quiet`）
   - 只显示错误信息（到stderr）
   - 不显示任何进度信息
   - 不显示统计信息
   - 不显示最终结果

3. **错误处理**
   - 错误信息始终输出到`stderr`
   - 错误信息包含"ERROR:"前缀，便于邮件筛选
   - 非零退出码指示失败状态

### 2.2 参数设计
- `-q, --quiet`：布尔选项，启用静默模式
- 默认值：`False`（显示所有信息）
- 互斥性：无其他日志相关参数（简化设计）

## 3. 技术设计

### 3.1 架构设计
```
chat_with_llm/
├── __init__.py
├── logutils.py          # 新增：统一日志模块
└── ...其他模块

scripts/
├── sum_hackernews.py    # 使用logutils.SumLogger
├── sum_reuters.py       # 使用logutils.SumLogger
├── sum_xwlb.py          # 使用logutils.SumLogger
├── sum_youtube.py       # 使用logutils.SumLogger
├── sum_yahoo_finance.py # 使用logutils.SumLogger
├── sum_hn_comments.py   # 使用logutils.SumLogger
└── sum_github_trending.py # 使用logutils.SumLogger
```

### 3.2 日志模块设计
```python
# chat_with_llm/logutils.py
class SumLogger:
    """统一的日志记录器，支持默认模式和静默模式"""
    def __init__(self, quiet=False):
        self.quiet = quiet

    def error(self, msg, *args):
        """错误信息：总是显示到stderr"""
        formatted_msg = msg % args if args else msg
        print(f"ERROR: {formatted_msg}", file=sys.stderr)

    def result(self, msg):
        """最终结果：非静默模式时显示"""
        if not self.quiet:
            print(msg)

    def info(self, msg, *args):
        """进度/统计信息：非静默模式时显示"""
        if not self.quiet:
            formatted_msg = msg % args if args else msg
            print(f"INFO: {formatted_msg}")

    def is_quiet(self):
        """检查是否为静默模式（用于控制tqdm等）"""
        return self.quiet
```

### 3.3 脚本集成模式
每个sum_xx.py脚本需要进行以下标准修改：

```python
# 1. 导入日志模块
from chat_with_llm import logutils

# 2. 添加参数
parser.add_argument('-q', '--quiet', action='store_true', default=False,
                   help='静默模式，只显示错误信息（不显示进度和结果）')

# 3. 创建日志记录器
args = parser.parse_args()
logger = logutils.SumLogger(quiet=args.quiet)

# 4. 替换现有print()调用（按类别）
# 错误信息 → logger.error()
# 进度信息 → logger.info()
# 最终结果 → logger.result()
```

### 3.4 输出示例对比

#### 默认模式（不带参数）
```
INFO: Fetching GitHub Trending page: https://github.com/trending
INFO: Found 13 projects on trending page
INFO: 13 projects after min_stars (100) filter
INFO: Processing 10 projects
INFO: Fetching README contents...
INFO: ✓ microsoft/PowerToys: README found at https://github.com/microsoft/PowerToys/blob/main/README.md
INFO: Starting analysis with model deepseek-chat...
## [microsoft/PowerToys](https://github.com/microsoft/PowerToys)
PowerToys 是微软官方推出的一套面向 Windows 系统的免费实用工具集...
```

#### 静默模式（-q）
```
ERROR: Failed to fetch https://example.com: Connection timeout
# 只有错误信息，无进度信息和最终结果
```

## 4. 实施计划

### 4.1 实施步骤
1. **创建日志模块**：编写`chat_with_llm/logutils.py`
2. **修改脚本**：按顺序修改7个sum_xx.py脚本
3. **测试验证**：测试每个脚本在默认模式和静默模式下的行为
4. **更新文档**：更新README或使用说明

### 4.2 修改顺序
1. `sum_github_trending.py`（最新创建，作为模板）
2. `sum_hackernews.py`（原始模板）
3. `sum_reuters.py`
4. `sum_xwlb.py`
5. `sum_youtube.py`
6. `sum_yahoo_fance.py`
7. `sum_hn_comments.py`

### 4.3 工作量估算
- 创建日志模块：15分钟
- 修改每个脚本：10分钟 × 7 = 70分钟
- 测试验证：30分钟
- **总计**：约2小时

## 5. 向后兼容性

### 5.1 行为兼容性
- **完全兼容**：默认行为（不带参数）与现有脚本完全一致
- **新增功能**：`-q`参数为新功能，不影响现有使用
- **错误处理**：错误信息格式保持不变，增加"ERROR:"前缀

### 5.2 API兼容性
- 仅添加可选参数，不修改现有参数
- 不改变脚本的输入/输出接口
- 不改变LLM调用方式

## 6. 测试计划

### 6.1 测试场景
1. **默认模式测试**：不带参数运行，验证所有信息正常显示
2. **静默模式测试**：使用`-q`参数运行，验证只显示错误信息
3. **错误场景测试**：模拟错误情况，验证错误信息正常显示
4. **tqdm集成测试**：验证静默模式下进度条被正确禁用

### 6.2 测试脚本
```bash
# 测试每个脚本的默认模式
python scripts/sum_github_trending.py --top_n 1 --dedup_n 0

# 测试静默模式
python scripts/sum_github_trending.py --top_n 1 --dedup_n 0 -q

# 测试错误情况（如无效URL）
python scripts/sum_youtube.py invalid_url
```

## 7. 计划任务配置建议

### 7.1 Cron配置示例
```bash
# 使用静默模式，只有错误会触发邮件通知
0 9 * * * cd /path/to/chat_with_llm && python scripts/sum_github_trending.py -q
0 10 * * * cd /path/to/chat_with_llm && python scripts/sum_hackernews.py -q
0 11 * * * cd /path/to/chat_with_llm && python scripts/sum_reuters.py -q
```

### 7.2 邮件通知配置
```bash
# crontab配置示例
MAILTO=your-email@example.com
# 静默模式下只有错误会发送邮件
```

## 8. 未来扩展性

### 8.1 可能的扩展
1. **日志级别**：未来可添加`-v/--verbose`支持多级别控制
2. **文件日志**：支持将日志输出到文件
3. **结构化日志**：支持JSON格式日志，便于分析
4. **性能监控**：添加执行时间统计

### 8.2 设计考虑
当前简化设计为未来扩展预留了接口：
- `SumLogger`类可扩展支持更多方法
- `quiet`参数可扩展为`log_level`枚举
- 架构支持添加新的输出处理器