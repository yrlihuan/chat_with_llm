# web.mrxwlb 模块

文件: `chat_with_llm/web/mrxwlb.py`

## 概述

每日新闻联播内容获取器, 数据源为 `cn.govopendata.com`.

## 类

### `MRXWLB(OnlineContent)`

注册名: `mrxwlb`

```python
MRXWLB(**params)
```

特有参数:
- `date_end`: 结束日期 (YYYYMMDD, 默认当天减 20 小时, 即当天晚上 8 点前取前一天)

#### `url2id(url) -> str`

从 URL 提取日期作为 site_id. 例: `https://cn.govopendata.com/xinwenlianbo/20250301/` → `20250301`

#### `id2url(site_id) -> str`

site_id 为 YYYYMMDD 格式日期, 拼接为完整 URL.

#### `list(n) -> list[str]`

返回从 `date_end` 往前 n 天的 URL 列表.

#### `fetch(url) -> (redirect_url, metadata, raw)`

调用 `linkseek.crawl()`, 使用浏览器模式获取 markdown.

#### `parse(url, raw) -> str`

直接返回 raw 内容, 不做额外处理.
