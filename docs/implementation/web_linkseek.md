# web.linkseek 模块

文件: `chat_with_llm/web/linkseek.py`

## 概述

LinkSeek 爬虫服务的 HTTP 客户端. LinkSeek 是一个独立部署的网页抓取服务, 支持浏览器渲染.

## 接口

### `crawl(url, formats=None, use_browser=True, proxy=None, mobile=False, timeout=30) -> (final_url, metadata, raw_content)`

调用 LinkSeek API 抓取页面.

参数:
- `url`: 目标 URL
- `formats`: 返回格式列表, 如 `["html"]` 或 `["markdown"]` (默认 `["html"]`)
- `use_browser`: 是否使用浏览器渲染 (默认 True)
- `proxy`: 代理名称 (在 LinkSeek 的 proxies.yaml 中配置)
- `mobile`: 移动端模式
- `timeout`: 超时秒数 (默认 30)

返回:
- `final_url`: 最终 URL (可能经过重定向)
- `metadata`: 元数据 dict (目前只提取 title)
- `raw_content`: 请求的第一个格式的内容

API 端点: `POST {LINKSEEK_BASE_URL}/api/v1/crawl`

错误处理:
- `ConnectionError` → 提示检查 LINKSEEK_BASE_URL 和服务状态
- `Timeout` → 提示超时
- HTTP 非 200 → 包含状态码和响应体
- JSON 中 `success=false` → 包含 error code/message 和 debug_id

### `get_base_url() -> str`

从 config 获取 LinkSeek 服务地址, 默认 `http://localhost:8000`.
