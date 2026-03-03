# web.hn_comments 模块

文件: `chat_with_llm/web/hn_comments.py`

## 概述

Hacker News 评论页获取与解析器. 继承自 `Crawl4AI`, 在 markdown 基础上进一步解析出评论树结构.

## 类

### `HNComments(Crawl4AI)`

注册名: `hn_comments`

```python
HNComments(**params)
```

默认参数覆盖:
- `parser='markdown'`, `use_proxy=True`, `strip_boilerplate=False`, `mean_delay='3'`

特有参数:
- `min_comments`: 最少评论数过滤 (默认 0)

#### `url2id(url) -> str`

从 `https://news.ycombinator.com/item?id=12345` 提取数字 ID.

#### `id2url(site_id) -> str`

拼接 HN item URL.

#### `list(n) -> list[str]`

获取 HN 首页热门帖子:
1. 使用 `crawl4ai` (link_extractor 模式) 抓取首页
2. XPath: `//span[@class="subline"]/a[3]` 提取评论链接
3. 解析评论数, 按评论数降序排列
4. 过滤 `min_comments`, 取前 n 个

#### `parse(url, raw) -> str`

将 HN 页面的 markdown 解析为结构化评论文本:

1. 调用父类 `Crawl4AI.parse()` 获取 markdown
2. 用正则从 markdown 表格中提取:
   - 评论 ID (从 vote 链接)
   - 用户名 (从 user 链接)
   - 父评论 ID (从 parent 链接)
   - 原帖标题和 URL (首条评论)
   - 评论内容 (reply 链接前的文本)
3. 递归计算每条评论的层级 (`update_and_get_level`)
4. 按出现顺序输出, 用缩进表示层级:
   - 原帖: `**[标题](URL)**`
   - 评论: `id: {id} (by {user}, reply to {parent_id}): {text}`
