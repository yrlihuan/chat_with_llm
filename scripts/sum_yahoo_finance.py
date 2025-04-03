import argparse
import collections
import json

from chat_with_llm import llm
from chat_with_llm.web import online_content as oc

import time
if __name__ == "__main__":
    dict_item_converter = lambda s: tuple([s[:s.index('=')], s[s.index('=')+1:]]) if '=' in s else (s, None)

    parser = argparse.ArgumentParser(description='Summarize financial news from Yahoo Finance.')

    candidate_prompts = {
        'v1': '以下是今天yahoo finance首页的文章. 文章之间用长--连线分割. 请根据内容总结今天的热点. 输出中文, 不限字数, 可以列举多个热点。',
    }

    parser.add_argument('-m', '--model', type=str, default='ds-chat', help='The model to use for generating summary')
    parser.add_argument('-p', '--prompt', default='v1')
    parser.add_argument('--llm_use_case', type=str, default='sum_yahoo', help='The use case for the llm model')
    parser.add_argument('--boilerplate_threshold', type=int, default=3, help='The threshold for boilerplate content')
    parser.add_argument('--params', nargs='+', type=dict_item_converter, default=[], help='Parameters for the online retriever')

    args = parser.parse_args()

    model_id = llm.get_model(args.model)
    home_retriever = oc.get_online_retriever(
        'crawl4ai',
        parser='link_extractor',
        link_extractor='//*[self::div and contains(@class, "content")] | (.//text())[1] | (.//@href)[1]',
        use_proxy=True,
        cache_expire=1)
    
    sub_retriever = oc.get_online_retriever(
        'crawl4ai',
        parser='markdown',
        use_proxy=True,
        strip_boilerplate=True,
        cache_expire=24*7,
        **dict(args.params))
    
    if args.prompt in candidate_prompts:
        prompt = candidate_prompts[args.prompt]
    else:
        prompt = args.prompt

    home_url = 'https://finance.yahoo.com/'
    json_links = home_retriever.retrieve(home_url)
    items = json.loads(json_links)

    urls = [link['url'] for link in items]
    if len(urls) == 0:
        print(f'No valid news link found in {home_url}')
        exit(1)

    # 通过统计多篇文章中出现的相同的行数来判断是否是多余的内容
    articles_contents = list(sub_retriever.retrieve_many(urls))
    boiloerplate_line_cnt = collections.defaultdict(int)
    for item, s in zip(items, articles_contents):
        item['content'] = s or ''
        for line in s.split('\n'):
            if line.strip():
                boiloerplate_line_cnt[line] += 1

    boiloerplate_lines = []
    for line, cnt in boiloerplate_line_cnt.items():
        if cnt >= args.boilerplate_threshold:
            boiloerplate_lines.append(line)

    contents = ''
    for item in items:
        if not item['content']:
            continue

        contents_stripped = item['content']
        for line in boiloerplate_lines:
            contents_stripped = contents_stripped.replace(line + '\n', '')

        if contents:
            contents += '-' * 80 + '\n'

        contents += f'({item["text"]})[{item["url"]}]\n'
        contents += contents_stripped + '\n'

    print(f'开始使用模型{model_id}进行分析...\n')

    message = llm.chat(prompt=prompt, contents=contents, model_id=model_id,
                       use_case=args.llm_use_case, save=True)
    print(message)
