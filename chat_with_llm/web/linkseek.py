import requests

from chat_with_llm import config

def get_base_url():
    return config.get('LINKSEEK_BASE_URL', 'http://localhost:8000')

def crawl(url, formats=None, use_browser=True, proxy=None, mobile=False, timeout=30):
    """调用 LinkSeek API 爬取 URL.

    Returns:
        (final_url, metadata, raw_content) 或在失败时抛出异常
    """
    if formats is None:
        formats = ["html"]

    payload = {
        "url": url,
        "formats": formats,
        "use_browser": use_browser,
        "timeout": timeout,
    }

    if proxy:
        payload["proxy"] = proxy

    if mobile:
        payload["mobile"] = True

    base_url = get_base_url()
    api_url = f"{base_url}/api/v1/crawl"

    try:
        response = requests.post(api_url, json=payload, timeout=timeout + 10)
    except requests.ConnectionError:
        raise RuntimeError(
            f'LinkSeek service unreachable at {base_url}. '
            f'Check LINKSEEK_BASE_URL in config.yaml and ensure the service is running.'
        )
    except requests.Timeout:
        raise RuntimeError(f'LinkSeek request timed out for {url} (timeout={timeout}s)')

    if response.status_code != 200:
        raise RuntimeError(
            f'LinkSeek returned HTTP {response.status_code} for {url}: {response.text[:500]}'
        )

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(
            f'LinkSeek returned non-JSON response for {url}: {response.text[:500]}'
        )

    if not data.get("success"):
        error = data.get("error", {})
        debug_id = data.get("debug_id", "unknown")
        msg = error.get("message", "") if isinstance(error, dict) else str(error)
        code = error.get("code", "UNKNOWN") if isinstance(error, dict) else "UNKNOWN"
        raise RuntimeError(
            f'LinkSeek crawl failed for {url}: {code} - {msg} '
            f'(debug_id: {debug_id}, response: {str(data)[:300]})'
        )

    result = data["data"]
    final_url = result["url"]

    # 返回请求的第一个格式的内容
    raw = result["formats"].get(formats[0], "")

    metadata = {}
    if result.get("metadata", {}).get("title"):
        metadata["title"] = result["metadata"]["title"]

    return final_url, metadata, raw
