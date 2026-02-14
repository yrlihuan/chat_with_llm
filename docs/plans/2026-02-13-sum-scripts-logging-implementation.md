# Sum脚本统一日志系统实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为所有sum_xx.py脚本添加统一的日志/静默模式控制，默认显示所有信息，-q/--quiet模式下只显示错误信息

**Architecture:** 创建chat_with_llm/logutils.py模块，包含SumLogger类；修改7个sum_xx.py脚本，用统一的日志方法替换print()调用

**Tech Stack:** Python 3.12+, argparse, sys.stderr

---

### Task 1: 创建logutils.py模块

**Files:**
- Create: `chat_with_llm/logutils.py`
- Modify: `chat_with_llm/__init__.py:1-10`

**Step 1: 创建logutils.py文件**

```python
"""
统一日志工具，用于控制sum_xx脚本的输出
默认显示所有信息，-q/--quiet模式下只显示错误
"""

import sys

class SumLogger:
    """
    统一的日志记录器，支持两种模式：
    - 默认模式：显示所有信息
    - 静默模式（-q）：只显示错误信息
    """
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

**Step 2: 更新__init__.py导出logutils**

在`chat_with_llm/__init__.py`末尾添加：
```python
# 导出logutils模块
from chat_with_llm import logutils
```

**Step 3: 验证模块创建**

Run: `python -c "from chat_with_llm import logutils; print('Module imported successfully')"`
Expected: "Module imported successfully"

**Step 4: 提交**

```bash
git add chat_with_llm/logutils.py chat_with_llm/__init__.py
git commit -m "feat: add logutils module for unified logging"
```

---

### Task 2: 修改sum_github_trending.py

**Files:**
- Modify: `scripts/sum_github_trending.py:1-10` (导入部分)
- Modify: `scripts/sum_github_trending.py:202-205` (参数解析)
- Modify: `scripts/sum_github_trending.py:225-230` (创建logger)
- Modify: `scripts/sum_github_trending.py:233-360` (替换print调用)

**Step 1: 添加导入和参数**

在文件开头导入部分添加：
```python
from chat_with_llm import logutils
```

在argparse部分添加：
```python
parser.add_argument('-q', '--quiet', action='store_true', default=False,
                   help='静默模式，只显示错误信息（不显示进度和结果）')
```

**Step 2: 创建logger实例**

在`args = parser.parse_args()`后添加：
```python
logger = logutils.SumLogger(quiet=args.quiet)
```

**Step 3: 替换print()调用**

查找并替换以下print调用：
- 第233行: `print(f'Fetching GitHub Trending page: {url}')` → `logger.info('Fetching GitHub Trending page: %s', url)`
- 第237行: `print(f'Found {len(projects)} projects on trending page')` → `logger.info('Found %d projects on trending page', len(projects))`
- 第240行: `print(f'{len(projects)} projects after min_stars ({args.min_stars}) filter')` → `logger.info('%d projects after min_stars (%d) filter', len(projects), args.min_stars)`
- 第242行: `print(f'{len(projects)} projects after language ({args.language}) filter')` → `logger.info('%d projects after language (%s) filter', len(projects), args.language)`
- 第249行: `print(f'Processing {len(projects)} projects')` → `logger.info('Processing %d projects', len(projects))`
- 第276行: `print(f'Removed {original_count - len(projects)} duplicate projects')` → `logger.info('Removed %d duplicate projects', original_count - len(projects))`
- 第283行: `print('No new projects to process (all are duplicates or filtered out)')` → `logger.info('No new projects to process (all are duplicates or filtered out)')`
- 第286行: `print('Fetching README contents...')` → `logger.info('Fetching README contents...')`
- 第294行: `print(f'  ✓ {project["full_name"]}: README found at {readme_url}')` → `logger.info('  ✓ %s: README found at %s', project["full_name"], readme_url)`
- 第297行: `print(f'  ✗ {project["full_name"]}: Failed to fetch {readme_url} - {e}')` → `logger.error('  ✗ %s: Failed to fetch %s - %s', project["full_name"], readme_url, e)`
- 第301行: `print(f'  ⚠ {project["full_name"]}: No README content found')` → `logger.info('  ⚠ %s: No README content found', project["full_name"])`
- 第329行: `print(f'\\nStarting analysis with model {model_id}...\\n')` → `logger.info('Starting analysis with model %s...', model_id)`
- 第341行: `print(message)` → `logger.result(message)`

**Step 4: 测试修改**

Run: `python scripts/sum_github_trending.py --top_n 1 --dedup_n 0 2>&1 | head -5`
Expected: 看到"INFO:"前缀的进度信息

Run: `python scripts/sum_github_trending.py --top_n 1 --dedup_n 0 -q 2>&1 | head -5`
Expected: 无输出（除非有错误）

**Step 5: 提交**

```bash
git add scripts/sum_github_trending.py
git commit -m "feat: add quiet mode to sum_github_trending.py"
```

---

### Task 3: 修改sum_hackernews.py

**Files:**
- Modify: `scripts/sum_hackernews.py:1-20` (导入部分)
- Modify: `scripts/sum_hackernews.py:177-180` (参数解析)
- Modify: `scripts/sum_hackernews.py:182-190` (创建logger)
- Modify: `scripts/sum_hackernews.py:200-350` (替换print调用)

**Step 1: 添加导入和参数**

在文件开头导入部分添加：
```python
from chat_with_llm import logutils
```

在argparse部分添加（第177行后）：
```python
parser.add_argument('-q', '--quiet', action='store_true', default=False,
                   help='静默模式，只显示错误信息（不显示进度和结果）')
```

**Step 2: 创建logger实例**

在`args = parser.parse_args()`后添加：
```python
logger = logutils.SumLogger(quiet=args.quiet)
```

**Step 3: 替换print()调用**

查找并替换以下print调用：
- 第200行: `print(f'Fetching {args.news_count} HackerNews articles...')` → `logger.info('Fetching %d HackerNews articles...', args.news_count)`
- 第204行: `print('Retrieved {len(titles)} articles')` → `logger.info('Retrieved %d articles', len(titles))`
- 第207行: `print(f'Filtering out articles with less than {args.min_comments} comments')` → `logger.info('Filtering out articles with less than %d comments', args.min_comments)`
- 第210行: `print(f'{len(articles)} articles after filter')` → `logger.info('%d articles after filter', len(articles))`
- 第226行: `print(f'Removed {original_count - len(articles)} duplicate articles')` → `logger.info('Removed %d duplicate articles', original_count - len(articles))`
- 第231行: `print('No new articles to process (all are duplicates)')` → `logger.info('No new articles to process (all are duplicates)')`
- 第247行: `print(f'Failed to retrieve article {url}: {e}')` → `logger.error('Failed to retrieve article %s: %s', url, e)`
- 第254行: `print(f'Starting analysis with model {model_id}...')` → `logger.info('Starting analysis with model %s...', model_id)`
- 第261行: `print('\\n' + '-' * 80 + '\\n')` → 保持原样（这是分隔符）
- 第262行: `print(message)` → `logger.result(message)`

**Step 4: 测试修改**

Run: `python scripts/sum_hackernews.py --news_count 1 --dedup_n 0 2>&1 | head -5`
Expected: 看到"INFO:"前缀的进度信息

Run: `python scripts/sum_hackernews.py --news_count 1 --dedup_n 0 -q 2>&1 | head -5`
Expected: 无输出（除非有错误）

**Step 5: 提交**

```bash
git add scripts/sum_hackernews.py
git commit -m "feat: add quiet mode to sum_hackernews.py"
```

---

### Task 4: 修改sum_reuters.py

**Files:**
- Modify: `scripts/sum_reuters.py:1-20` (导入部分)
- Modify: `scripts/sum_reuters.py:84-87` (参数解析)
- Modify: `scripts/sum_reuters.py:89-95` (创建logger)
- Modify: `scripts/sum_reuters.py:105-200` (替换print调用)

**Step 1: 添加导入和参数**

在文件开头导入部分添加：
```python
from chat_with_llm import logutils
```

在argparse部分添加（第84行后）：
```python
parser.add_argument('-q', '--quiet', action='store_true', default=False,
                   help='静默模式，只显示错误信息（不显示进度和结果）')
```

**Step 2: 创建logger实例**

在`args = parser.parse_args()`后添加：
```python
logger = logutils.SumLogger(quiet=args.quiet)
```

**Step 3: 替换print()调用**

查找并替换以下print调用：
- 第105行: `print(f'Fetching Reuters content...')` → `logger.info('Fetching Reuters content...')`
- 第108行: `print(f'Retrieved {len(items)} items')` → `logger.info('Retrieved %d items', len(items))`
- 第112行: `print(f'No content retrieved, exiting.')` → `logger.info('No content retrieved, exiting.')`
- 第116行: `print(f'Removed {original_count - len(items)} duplicate items')` → `logger.info('Removed %d duplicate items', original_count - len(items))`
- 第120行: `print('No new items to process (all are duplicates)')` → `logger.info('No new items to process (all are duplicates)')`
- 第130行: `print(f'Failed to retrieve article {url}: {e}')` → `logger.error('Failed to retrieve article %s: %s', url, e)`
- 第137行: `print(f'Starting analysis with model {model_id}...')` → `logger.info('Starting analysis with model %s...', model_id)`
- 第144行: `print('\\n' + '-' * 80 + '\\n')` → 保持原样
- 第145行: `print(message)` → `logger.result(message)`

**Step 4: 测试修改**

Run: `python scripts/sum_reuters.py --news_count 1 --dedup_n 0 2>&1 | head -5`
Expected: 看到"INFO:"前缀的进度信息

**Step 5: 提交**

```bash
git add scripts/sum_reuters.py
git commit -m "feat: add quiet mode to sum_reuters.py"
```

---

### Task 5: 修改sum_xwlb.py

**Files:**
- Modify: `scripts/sum_xwlb.py:1-30` (导入部分)
- Modify: `scripts/sum_xwlb.py:95-98` (参数解析)
- Modify: `scripts/sum_xwlb.py:100-110` (创建logger)
- Modify: `scripts/sum_xwlb.py:120-300` (替换print调用)

**Step 1: 添加导入和参数**

在文件开头导入部分添加：
```python
from chat_with_llm import logutils
```

在argparse部分添加（第95行后）：
```python
parser.add_argument('-q', '--quiet', action='store_true', default=False,
                   help='静默模式，只显示错误信息（不显示进度和结果）')
```

**Step 2: 创建logger实例**

在`args = parser.parse_args()`后添加：
```python
logger = logutils.SumLogger(quiet=args.quiet)
```

**Step 3: 替换print()调用**

查找并替换以下print调用：
- 第120行: `print(f'Processing date: {date_str}')` → `logger.info('Processing date: %s', date_str)`
- 第124行: `print(f'Failed to fetch content for {date_str}: {e}')` → `logger.error('Failed to fetch content for %s: %s', date_str, e)`
- 第130行: `print(f'No content for {date_str}')` → `logger.info('No content for %s', date_str)`
- 第140行: `print(f'Starting analysis with model {model_id}...')` → `logger.info('Starting analysis with model %s...', model_id)`
- 第147行: `print('\\n' + '-' * 80 + '\\n')` → 保持原样
- 第148行: `print(message)` → `logger.result(message)`

**Step 4: 测试修改**

Run: `python scripts/sum_xwlb.py --date $(date +%Y%m%d) --step 1 2>&1 | head -5`
Expected: 看到"INFO:"前缀的进度信息或"No content"信息

**Step 5: 提交**

```bash
git add scripts/sum_xwlb.py
git commit -m "feat: add quiet mode to sum_xwlb.py"
```

---

### Task 6: 修改sum_youtube.py

**Files:**
- Modify: `scripts/sum_youtube.py:1-20` (导入部分)
- Modify: `scripts/sum_youtube.py:48-51` (参数解析)
- Modify: `scripts/sum_youtube.py:53-60` (创建logger)
- Modify: `scripts/sum_youtube.py:65-150` (替换print调用)

**Step 1: 添加导入和参数**

在文件开头导入部分添加：
```python
from chat_with_llm import logutils
```

在argparse部分添加（第48行后）：
```python
parser.add_argument('-q', '--quiet', action='store_true', default=False,
                   help='静默模式，只显示错误信息（不显示进度和结果）')
```

**Step 2: 创建logger实例**

在`args = parser.parse_args()`后添加：
```python
logger = logutils.SumLogger(quiet=args.quiet)
```

**Step 3: 替换print()调用**

查找并替换以下print调用：
- 第65行: `print(f'Processing YouTube link: {args.youtube_link}')` → `logger.info('Processing YouTube link: %s', args.youtube_link)`
- 第70行: `print(f'Failed to retrieve video info: {e}')` → `logger.error('Failed to retrieve video info: %s', e)`
- 第76行: `print(f'No subtitles found for {args.youtube_link}')` → `logger.info('No subtitles found for %s', args.youtube_link)`
- 第82行: `print(f'Starting analysis with model {model_id}...')` → `logger.info('Starting analysis with model %s...', model_id)`
- 第89行: `print('\\n' + '-' * 80 + '\\n')` → 保持原样
- 第90行: `print(message)` → `logger.result(message)`

**Step 4: 测试修改**

Run: `python scripts/sum_youtube.py https://www.youtube.com/watch?v=dQw4w9WgXcQ 2>&1 | head -5`
Expected: 看到"INFO:"前缀的进度信息或错误信息

**Step 5: 提交**

```bash
git add scripts/sum_youtube.py
git commit -m "feat: add quiet mode to sum_youtube.py"
```

---

### Task 7: 修改sum_yahoo_finance.py

**Files:**
- Modify: `scripts/sum_yahoo_finance.py:1-20` (导入部分)
- Modify: `scripts/sum_yahoo_finance.py:76-79` (参数解析)
- Modify: `scripts/sum_yahoo_finance.py:81-90` (创建logger)
- Modify: `scripts/sum_yahoo_finance.py:100-250` (替换print调用)

**Step 1: 添加导入和参数**

在文件开头导入部分添加：
```python
from chat_with_llm import logutils
```

在argparse部分添加（第76行后）：
```python
parser.add_argument('-q', '--quiet', action='store_true', default=False,
                   help='静默模式，只显示错误信息（不显示进度和结果）')
```

**Step 2: 创建logger实例**

在`args = parser.parse_args()`后添加：
```python
logger = logutils.SumLogger(quiet=args.quiet)
```

**Step 3: 替换print()调用**

查找并替换以下print调用：
- 第100行: `print(f'Fetching Yahoo Finance content...')` → `logger.info('Fetching Yahoo Finance content...')`
- 第103行: `print(f'Retrieved {len(items)} items')` → `logger.info('Retrieved %d items', len(items))`
- 第107行: `print(f'No content retrieved, exiting.')` → `logger.info('No content retrieved, exiting.')`
- 第111行: `print(f'Removed {original_count - len(items)} duplicate items')` → `logger.info('Removed %d duplicate items', original_count - len(items))`
- 第115行: `print('No new items to process (all are duplicates)')` → `logger.info('No new items to process (all are duplicates)')`
- 第125行: `print(f'Failed to retrieve article {url}: {e}')` → `logger.error('Failed to retrieve article %s: %s', url, e)`
- 第132行: `print(f'Starting analysis with model {model_id}...')` → `logger.info('Starting analysis with model %s...', model_id)`
- 第139行: `print('\\n' + '-' * 80 + '\\n')` → 保持原样
- 第140行: `print(message)` → `logger.result(message)`

**Step 4: 测试修改**

Run: `python scripts/sum_yahoo_finance.py --news_count 1 --dedup_n 0 2>&1 | head -5`
Expected: 看到"INFO:"前缀的进度信息

**Step 5: 提交**

```bash
git add scripts/sum_yahoo_finance.py
git commit -m "feat: add quiet mode to sum_yahoo_finance.py"
```

---

### Task 8: 修改sum_hn_comments.py

**Files:**
- Modify: `scripts/sum_hn_comments.py:1-20` (导入部分)
- Modify: `scripts/sum_hn_comments.py:120-123` (参数解析)
- Modify: `scripts/sum_hn_comments.py:125-135` (创建logger)
- Modify: `scripts/sum_hn_comments.py:145-350` (替换print调用)

**Step 1: 添加导入和参数**

在文件开头导入部分添加：
```python
from chat_with_llm import logutils
```

在argparse部分添加（第120行后）：
```python
parser.add_argument('-q', '--quiet', action='store_true', default=False,
                   help='静默模式，只显示错误信息（不显示进度和结果）')
```

**Step 2: 创建logger实例**

在`args = parser.parse_args()`后添加：
```python
logger = logutils.SumLogger(quiet=args.quiet)
```

**Step 3: 替换print()调用**

查找并替换以下print调用：
- 第145行: `print(f'Processing HackerNews comments...')` → `logger.info('Processing HackerNews comments...')`
- 第150行: `print(f'Retrieved {len(items)} items')` → `logger.info('Retrieved %d items', len(items))`
- 第155行: `print(f'No items found, exiting.')` → `logger.info('No items found, exiting.')`
- 第160行: `print(f'Removed {original_count - len(items)} duplicate items')` → `logger.info('Removed %d duplicate items', original_count - len(items))`
- 第165行: `print('No new items to process (all are duplicates)')` → `logger.info('No new items to process (all are duplicates)')`
- 第180行: `print(f'Failed to retrieve comments for {url}: {e}')` → `logger.error('Failed to retrieve comments for %s: %s', url, e)`
- 第190行: `print(f'Starting analysis with model {model_id}...')` → `logger.info('Starting analysis with model %s...', model_id)`
- 第200行: `print('\\n' + '-' * 80 + '\\n')` → 保持原样
- 第201行: `print(message)` → `logger.result(message)`

**Step 4: 测试修改**

Run: `python scripts/sum_hn_comments.py --daily_topn 1 --dedup_n 0 2>&1 | head -5`
Expected: 看到"INFO:"前缀的进度信息

**Step 5: 提交**

```bash
git add scripts/sum_hn_comments.py
git commit -m "feat: add quiet mode to sum_hn_comments.py"
```

---

### Task 9: 集成测试和验证

**Files:**
- Test: `scripts/sum_github_trending.py`
- Test: `scripts/sum_hackernews.py`
- Test: `scripts/sum_reuters.py`
- Test: `scripts/sum_xwlb.py`
- Test: `scripts/sum_youtube.py`
- Test: `scripts/sum_yahoo_finance.py`
- Test: `scripts/sum_hn_comments.py`

**Step 1: 测试默认模式**

Run: `python scripts/sum_github_trending.py --top_n 1 --dedup_n 0 2>&1 | grep -E "INFO:|ERROR:" | head -5`
Expected: 看到"INFO:"前缀的输出

**Step 2: 测试静默模式**

Run: `python scripts/sum_github_trending.py --top_n 1 --dedup_n 0 -q 2>&1 | grep -E "INFO:|ERROR:" | wc -l`
Expected: 0（除非有错误）

**Step 3: 测试错误处理**

Run: `python scripts/sum_youtube.py invalid_url 2>&1 | grep "ERROR:"`
Expected: 看到"ERROR:"前缀的错误信息

**Step 4: 验证所有脚本**

创建一个测试脚本`test_logging.py`：
```python
#!/usr/bin/env python3
import subprocess

scripts = [
    "sum_github_trending.py --top_n 1 --dedup_n 0",
    "sum_hackernews.py --news_count 1 --dedup_n 0",
    "sum_reuters.py --news_count 1 --dedup_n 0",
    "sum_xwlb.py --date 20240213 --step 1",
    "sum_yahoo_finance.py --news_count 1 --dedup_n 0",
    "sum_hn_comments.py --daily_topn 1 --dedup_n 0",
]

for script in scripts:
    cmd = f"python scripts/{script} -q 2>&1"
    print(f"Testing: {script}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0 and "ERROR:" not in result.stderr:
        print(f"  WARNING: {script} returned non-zero but no ERROR: prefix")
    elif len(result.stdout.strip()) > 0:
        print(f"  WARNING: {script} produced output in quiet mode")
    else:
        print(f"  OK: {script} quiet mode works")
```

Run: `python test_logging.py`
Expected: 所有脚本通过基本测试

**Step 5: 提交测试结果**

```bash
git add test_logging.py
git commit -m "test: add logging integration test script"
```

---

Plan complete and saved to `docs/plans/2026-02-13-sum-scripts-logging-implementation.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**