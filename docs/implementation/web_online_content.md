# web.online_content 模块

文件: `chat_with_llm/web/online_content.py`

## 概述

网页内容抓取框架的核心, 定义了 fetch → cache → parse 的标准流程, 以及基于注册表的 retriever 管理.

## 类

### `OnlineContent` (ABC)

所有网页内容获取器的基类.

```python
OnlineContent(**params)
```

必需参数:
- `name`: retriever 名称, 同时作为 web_cache 的 identifier

可选参数:
- `description`: 描述
- `force_fetch`: 强制重新抓取 (忽略 raw 缓存)
- `force_parse`: 强制重新解析 (忽略 parsed 缓存)
- `update_cache`: 是否更新缓存 (默认 True)
- `num_workers`: 并发线程数 (默认取 config `ONLINE_CONTENT_WORKERS`)

#### 核心流程: `retrieve_many(urls_or_ids) -> list[str]`

对每个 url_or_id:
1. 调用 `parse_url_id()` 解析出 url 和 site_id
2. 检查缓存:
   - 有 `.raw` 缓存且不 force_fetch → 检查 `.parsed` 缓存
   - 有 `.parsed` 且不 force_parse → 直接返回缓存
   - 否则用缓存的 raw 重新 parse
3. 无缓存 → 批量 fetch → parse → 保存

#### `retrieve(url_or_id) -> str`

单条 retrieve, 内部调用 `retrieve_many`.

#### `fetch_many(urls) -> list`

使用 `ThreadPoolExecutor` 并发调用 `fetch()`, 线程数由 `num_workers` 控制.

#### 缓存文件结构

每个 site_id 对应三个文件:
- `{site_id}.meta`: JSON 格式元数据 (url, redirect_url, title 等)
- `{site_id}.raw`: 原始抓取内容
- `{site_id}.parsed`: 解析后的文本

#### 子类必须实现的抽象方法

| 方法 | 说明 |
|------|------|
| `url2id(url) -> str` | 从 URL 提取 site_id |
| `id2url(site_id) -> str` | 从 site_id 还原 URL |
| `list(n) -> list[str]` | 列出 n 个可抓取的 URL |
| `fetch(url) -> (redirect_url, metadata, raw)` | 抓取单个页面 |
| `parse(url, raw) -> str` | 将原始内容解析为文本 |

### `AsyncOnlineContent(OnlineContent)`

异步版本基类, 将 `fetch_many` 替换为 `asyncio.run(async_fetch_many)`.

子类需实现 `async_fetch(url)` 而非 `fetch(url)`.

使用 `asyncio.Semaphore` 控制并发 (但当前实现中 semaphore 未实际应用到任务上).

## 注册表

### `add_online_retriever(name, retriever_class)`

注册 retriever 类. name 不可重复.

### `get_online_retriever(name, **params) -> OnlineContent`

创建并返回指定名称的 retriever 实例, `params` 传递给构造函数.

### `list_online_retrievers() -> list[str]`

列出所有已注册的 retriever 名称.

## 已注册的 Retriever

模块导入 `chat_with_llm.web` 时自动注册:
- `crawl4ai`: 通用网页爬虫 (见 c4ai.md)
- `mrxwlb`: 新闻联播 (见 mrxwlb.md)
- `hn_comments`: HN 评论 (见 hn_comments.md)
