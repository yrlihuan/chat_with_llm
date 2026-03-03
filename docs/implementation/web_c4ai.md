# web.c4ai 模块 (Crawl4AI)

文件: `chat_with_llm/web/c4ai.py`

## 概述

通用网页爬虫, 通过 LinkSeek 服务抓取页面, 支持 markdown 输出和 XPath 链接提取两种解析模式.

## 类

### `Crawl4AI(OnlineContent)`

注册名: `crawl4ai`

```python
Crawl4AI(**params)
```

参数:
- `cache_expire`: 缓存过期时间 (小时, 默认 168 即 7 天)
- `use_proxy`: 是否使用代理 (默认 False)
- `mobile_mode`: 移动端模式 (默认 False)
- `parser`: 解析器类型, `'markdown'` 或 `'link_extractor'` (默认 `'markdown'`)
- `link_extractor`: XPath 表达式, 仅 parser=link_extractor 时使用
- `strip_boilerplate`: 去除链接密集行 (默认 False)

#### `url2id(url) -> str`

生成缓存 key, 格式: `{reversed_domain}_{path_md5_8}_{time_tag}`

- 域名反转: `news.ycombinator` → `ycombinator_news`
- 去除 `www.` 前缀和 `.com` 后缀
- path 取 MD5 前 8 位
- time_tag: 基于 `cache_expire` 对齐的时间戳 (`YYYYMMDDHH`), 确保同一缓存周期内的请求命中同一缓存

#### `id2url(site_id) -> None`

因为 url2id 使用了哈希, 无法反向还原, 始终返回 None.

#### `parse(url, raw) -> str`

两种模式:
1. **markdown**: 直接返回 raw (LinkSeek 已返回 markdown), 可选 strip_boilerplate
2. **link_extractor**: 使用 lxml 按 XPath 提取链接, 返回 JSON 数组 `[{url, text}]`

link_extractor 的 XPath 格式: `element_path [| text_sub_path] [| href_sub_path]`, 用 `|` 分隔 (注意: XPath 中的 `|` 需用 `or` 替代).

#### `fetch(url) -> (redirect_url, metadata, raw)`

调用 `linkseek.crawl()`:
- parser=link_extractor 时请求 HTML 格式
- 其他情况请求 markdown 格式
- 使用浏览器模式 (`use_browser=True`)
