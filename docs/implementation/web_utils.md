# web.utils 模块

文件: `chat_with_llm/web/utils.py`

## 概述

网页内容处理的工具函数集合, 主要用于清理网页抓取后的 markdown 文本.

## 接口

### `url_to_site(url) -> str`

提取 URL 的主域名. 例: `https://www.reddit.com/r/foo` → `reddit.com`.

实现: 维护一个常见顶级域名集合 (com, org, co, io, ai, cn 等), 从域名尾部向前扫描, 遇到非 TLD 部分时停止.

### `extract_links_from_markdown(s) -> list[(start, end, text)]`

从 markdown 文本中提取所有 `[text](url)` 格式的链接.

返回元组列表:
- `start`: 链接在字符串中的起始位置
- `end`: 结束位置
- `text`: 链接文本

实现: 手工状态机逐字符扫描, 跟踪方括号和圆括号的嵌套层级.

### `strip_boilerplate(contents) -> str`

去除以链接为主的行 (通常是导航栏、侧边栏等样板内容).

规则:
- 如果一行中链接文本占总长度的 90% 以上, 整行删除
- 其余行中的 `[text](url)` 替换为 `text` (去除链接但保留文字)

### `remove_duplicated_lines(contents, threshold, whitelist_prefixes=[]) -> str`

通过统计行重复次数来去除样板内容 (适用于多篇文章合并后的文本).

参数:
- `threshold`: 出现次数 >= threshold 的行视为样板 (必须 > 1)
- `whitelist_prefixes`: 白名单前缀, 匹配的行不会被删除

额外处理: 将连续 3 个以上空行压缩为 2 个空行.
