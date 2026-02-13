import argparse
import re
import time
from urllib.parse import urljoin

from chat_with_llm import llm
from chat_with_llm.web import online_content as oc

def extract_projects(contents):
    """
    从GitHub Trending页面Markdown格式内容中提取项目信息

    格式示例:
    [ Star  ](https://github.com/login?return_to=%2Ftambo-ai%2Ftambo)
    ##  [ tambo-ai /  tambo](https://github.com/tambo-ai/tambo)
    Generative UI SDK for React
    TypeScript [ 9,202](https://github.com/tambo-ai/tambo/stargazers) [ 440](https://github.com/tambo-ai/tambo/forks) Built by ... 300 stars today

    返回项目信息列表，每个项目包含:
    - url: 项目完整URL
    - owner: 仓库所有者
    - repo: 仓库名
    - full_name: owner/repo
    - description: 项目描述
    - language: 主要编程语言
    - stars: 星标总数
    - stars_today: 今日新增星标数
    """
    import re
    projects = []
    lines = contents.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        # 查找项目标题行: 包含 "##  [ owner /  repo](https://github.com/owner/repo)"
        if line.strip().startswith('##') and '](https://github.com/' in line:
            project = {}

            # 提取仓库URL - 更灵活的正则表达式
            # 匹配: ##  [ tambo-ai /  tambo](https://github.com/tambo-ai/tambo)
            url_pattern = r'https://github\.com/[^/]+/[^)]+'
            url_match = re.search(url_pattern, line)
            if url_match:
                url = url_match.group(0)
                project['url'] = url
                # 从URL提取owner和repo
                parts = url.split('/')
                if len(parts) >= 5:
                    project['owner'] = parts[3]
                    project['repo'] = parts[4]
                    project['full_name'] = f"{parts[3]}/{parts[4]}"
                else:
                    # 从标题行提取
                    title_pattern = r'\[ ([^/]+) /  ([^\]]+) \]'
                    title_match = re.search(title_pattern, line)
                    if title_match:
                        project['owner'] = title_match.group(1).strip()
                        project['repo'] = title_match.group(2).strip()
                        project['full_name'] = f"{project['owner']}/{project['repo']}"
                    else:
                        # 备用: 从括号内提取
                        bracket_pattern = r'\[ ([^\]]+) \]'
                        bracket_match = re.search(bracket_pattern, line)
                        if bracket_match:
                            full_name = bracket_match.group(1).strip()
                            if '/' in full_name:
                                owner, repo = full_name.split('/', 1)
                                project['owner'] = owner.strip()
                                project['repo'] = repo.strip()
                                project['full_name'] = full_name

            # 如果没有提取到URL，跳过
            if 'url' not in project:
                i += 1
                continue

            # 下一行可能是描述
            project['description'] = ''
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # 描述行通常不以特殊字符开头，有一定长度
                if (len(next_line) > 10 and
                    not next_line.startswith('[') and
                    not next_line.startswith('##') and
                    not next_line.startswith('TypeScript') and
                    not next_line.startswith('Python') and
                    not next_line.startswith('JavaScript') and
                    not re.match(r'^[A-Z][a-z]+ \[', next_line)):
                    project['description'] = next_line

            # 查找语言和星标行（通常在描述行之后）
            project['language'] = 'Unknown'
            project['stars'] = 0
            project['stars_today'] = 0

            search_start = i + 2 if project['description'] else i + 1
            for j in range(search_start, min(len(lines), search_start + 3)):
                lang_line = lines[j]

                # 检查是否包含星标链接
                if 'stargazers' in lang_line:
                    # 提取编程语言（行首的第一个单词）
                    words = lang_line.strip().split()
                    if words:
                        project['language'] = words[0]

                    # 提取星标数: [ 9,202](https://.../stargazers)
                    stars_pattern = r'\[ ([\d,]+)\]\([^)]*/stargazers\)'
                    stars_match = re.search(stars_pattern, lang_line)
                    if stars_match:
                        stars_str = stars_match.group(1).replace(',', '')
                        try:
                            project['stars'] = int(stars_str)
                        except:
                            project['stars'] = 0

                    # 提取今日新增星标
                    today_pattern = r'(\d+(?:,\d+)*)\s+stars today'
                    today_match = re.search(today_pattern, lang_line)
                    if today_match:
                        today_str = today_match.group(1).replace(',', '')
                        try:
                            project['stars_today'] = int(today_str)
                        except:
                            project['stars_today'] = 0

                    break

            projects.append(project)

        i += 1

    return projects

def build_readme_url(project):
    """
    构建README页面的URL

    尝试可能的README路径:
    1. https://github.com/{owner}/{repo}/blob/main/README.md
    2. https://github.com/{owner}/{repo}/blob/master/README.md
    3. https://github.com/{owner}/{repo}#readme (备用)
    """
    base_url = project['url']
    readme_urls = [
        f"{base_url}/blob/main/README.md",
        f"{base_url}/blob/master/README.md",
        f"{base_url}#readme"
    ]
    return readme_urls

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Summarize GitHub Trending projects daily.')

    candidate_prompts = {
        'v1': '你是一个技术分析师，需要总结GitHub热门项目。以下是今天GitHub Trending上的热门项目信息，每个项目包含仓库链接、描述、编程语言、星标数和README预览。项目之间用80个连字符分隔。\n\n'
              '请为每个项目生成中文总结，包含以下部分：\n'
              '1. 项目用途和核心功能（100-150字）\n'
              '2. 技术栈和架构特点（80-100字）\n'
              '3. 关键特性和创新点（80-100字）\n'
              '4. 学习价值和应用场景建议（80-100字）\n'
              '5. 与其他类似项目的对比（可选）\n\n'
              '输出格式：\n'
              '为每个项目单独输出，格式为：\n'
              '## [仓库名称](仓库链接)\n'
              '**描述**: 项目描述\n'
              '**语言**: 编程语言\n'
              '**星标**: 总数 (今日新增)\n'
              '**总结**: [你的总结内容]\n\n'
              '---\n',
        'v2': '你是一个技术分析师，需要为GitHub Trending热门项目生成适合语音播报的中文总结。以下是项目信息：仓库链接、描述、编程语言、星标数和README预览。\n\n'
              '总结要求：\n'
              '1. 开头自然介绍项目，包含项目名称、主要编程语言和星标数（例如："微软的PowerToys项目，使用C#语言开发，拥有12.9万星标"）\n'
              '2. 简要描述项目是什么，用一两句话概括\n'
              '3. 详细说明项目的核心功能和作用（这是重点内容）\n'
              '4. 分析项目的技术特点、创新之处，并可以与其他类似项目进行对比\n\n'
              '输出要求：\n'
              '- 语言自然流畅，口语化，适合语音播报\n'
              '- 避免使用死板的编号格式（如1. 2. 3.）\n'
              '- 使用自然的过渡词连接各部分内容\n'
              '- 每个项目总结控制在300-400字\n'
              '- 在项目之间用"---"分隔\n\n'
              '请根据每个项目的实际情况灵活组织内容，确保总结清晰易懂，适合通过TTS转换为语音收听。\n',
        'v3': '你是一个技术分析师，需要分析GitHub Trending热门项目并生成中文总结。以下是项目信息：仓库链接、描述、编程语言、星标数和README预览。\n\n'
              '总结要求：\n'
              '1. 首先输出项目名称 格式 "## [仓库名称](仓库链接)"\n'
              '2. 然后详细说明项目的核心功能和作用\n'
              '3. 最后分析项目的技术特点、创新之处，可以与其他类似项目进行对比\n\n'
              '输出要求：\n'
              '- 语言自然流畅，表达清晰\n'
              '- 每个项目总结控制在300-400字\n'
              '- 在项目之间用"---"分隔\n\n'
    }

    parser.add_argument('-m', '--model', type=str, default='ds-chat', help='The model to use for generating summary')
    parser.add_argument('-p', '--prompt', default='v3')
    parser.add_argument('-l', '--language', type=str, default='', help='Filter by programming language (e.g., python, javascript)')
    parser.add_argument('-s', '--since', type=str, default='daily', choices=['daily', 'weekly', 'monthly'], help='Time range for trending')
    parser.add_argument('--top_n', type=int, default=10, help='Number of top projects to process')
    parser.add_argument('--min_stars', type=int, default=100, help='Minimum number of stars to consider')
    parser.add_argument('-d', '--dedup_n', type=int, default=4, help='Remove duplicate projects from the last n runs.')
    parser.add_argument('--llm_use_case', type=str, default='sum_github_trending', help='The use case for the llm model')
    parser.add_argument('--use_proxy', action='store_true', default=True, help='Use proxy for GitHub access')
    parser.add_argument('--no-proxy', dest='use_proxy', action='store_false', help='Do not use proxy for GitHub access')

    args = parser.parse_args()

    model_id = llm.get_model(args.model)

    # 获取Trending页面检索器（不清理样板内容，保留原始HTML结构）
    trending_retriever = oc.get_online_retriever('crawl4ai',
                                                 strip_boilerplate=False,
                                                 use_proxy=args.use_proxy,
                                                 cache_expire=1,
                                                 force_fetch=True)

    # 获取README页面检索器（清理样板内容，提取主要文本）
    readme_retriever = oc.get_online_retriever('crawl4ai',
                                               strip_boilerplate=True,
                                               use_proxy=args.use_proxy,
                                               cache_expire=24*7)


    # 构建GitHub Trending URL
    base_url = 'https://github.com/trending'
    if args.language:
        url = f'{base_url}/{args.language}?since={args.since}'
    else:
        url = f'{base_url}?since={args.since}'

    print(f'Fetching GitHub Trending page: {url}')

    # 抓取Trending页面
    trending_content = trending_retriever.retrieve(url)

    # 提取项目信息
    projects = extract_projects(trending_content)

    print(f'Found {len(projects)} projects on trending page')

    # 按星标数过滤
    projects = [p for p in projects if p['stars'] >= args.min_stars]
    print(f'{len(projects)} projects after min_stars ({args.min_stars}) filter')

    # 按编程语言过滤（如果指定）
    if args.language:
        projects = [p for p in projects if args.language.lower() in p['language'].lower()]
        print(f'{len(projects)} projects after language ({args.language}) filter')

    # 按星标数排序（降序）
    projects.sort(key=lambda x: -x['stars'])

    # 限制处理数量
    if args.top_n > 0:
        projects = projects[:args.top_n]

    print(f'Processing {len(projects)} projects')

    # 重复检测
    chat_history_storage = llm.get_storage(args.llm_use_case)
    if args.dedup_n > 0:
        # 读取最近的聊天记录
        files = chat_history_storage.list()
        files = list(filter(lambda x: x.endswith('.input.txt'), files))
        files.sort(reverse=True)

        recent = files[:min(args.dedup_n, len(files))]
        processed_urls = set()

        for f in recent:
            recent_contents = chat_history_storage.load(f)
            # 每行可能包含项目信息，格式为：[full_name](url) 或 纯URL
            for line in recent_contents.split('\n'):
                line = line.strip()
                if not line:
                    continue

                # 尝试提取Markdown链接格式中的URL: [text](url)
                import re
                url_match = re.search(r'\[.*?\]\((https?://[^)]+)\)', line)
                if url_match:
                    url = url_match.group(1)
                    processed_urls.add(url)
                elif line.startswith('http'):
                    # 如果是纯URL
                    processed_urls.add(line)
                # 否则忽略这一行

        # 过滤已处理的项目
        original_count = len(projects)
        projects = [p for p in projects if p['url'] not in processed_urls]
        print(f'Removed {original_count - len(projects)} duplicate projects')

    if len(projects) == 0:
        print('No new projects to process (all are duplicates or filtered out)')
        exit(0)

    # 为每个项目抓取README内容
    print('Fetching README contents...')
    for project in projects:
        readme_urls = build_readme_url(project)
        readme_content = ''

        # 尝试不同的README URL
        for readme_url in readme_urls:
            try:
                content = readme_retriever.retrieve(readme_url)
                if content and len(content.strip()) > 100:  # 简单检查是否有足够内容
                    readme_content = content
                    print(f'  ✓ {project["full_name"]}: README found at {readme_url}')
                    break
            except Exception as e:
                print(f'  ✗ {project["full_name"]}: Failed to fetch {readme_url} - {e}')
                continue

        project['readme_content'] = readme_content
        if not readme_content:
            print(f'  ⚠ {project["full_name"]}: No README content found')

    # 准备LLM输入内容（类似sum_hackernews.py的格式）
    contents = ''
    for i, project in enumerate(projects):
        if i > 0:
            contents += '-' * 80 + '\n'

        # 项目标题和链接（用于去重）
        contents += f'[{project["full_name"]}]({project["url"]})\n'

        # 项目基本信息
        contents += f'描述: {project["description"]}\n'
        contents += f'编程语言: {project["language"]}\n'
        contents += f'星标总数: {project["stars"]} (今日新增: {project["stars_today"]})\n'

        # README内容（截断以避免过长）
        readme_preview = project['readme_content'][:3000] if project['readme_content'] else '（无README内容）'
        contents += f'README预览:\n{readme_preview}\n'

    print(f'\nStarting analysis with model {model_id}...\n')

    # 调用LLM生成总结
    # 使用候选提示词中的v1版本
    if args.prompt in candidate_prompts:
        prompt = candidate_prompts[args.prompt]
    else:
        prompt = args.prompt

    message = llm.chat(prompt=prompt,
                       contents=contents,
                       model_id=model_id,
                       use_case=args.llm_use_case,
                       save=True)

    print(message)
