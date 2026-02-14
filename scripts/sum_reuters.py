import argparse
import collections
import json
import sys

from chat_with_llm import llm
from chat_with_llm import logutils
from chat_with_llm.web import online_content as oc
from chat_with_llm.web import utils as web_utils

if __name__ == "__main__":
    dict_item_converter = lambda s: tuple([s[:s.index('=')], s[s.index('=')+1:]]) if '=' in s else (s, None)

    parser = argparse.ArgumentParser(description='Summarize financial news from Reuters.')

    candidate_prompts = {
        'v1': '以下是今天reuters/business首页的文章. 文章之间用长--连线分割. 请根据内容总结今天的热点. 输出中文, 不限字数, 可以列举多个热点。',
    }

    parser.add_argument('-m', '--model', type=str, default='gemini-2.0-pro', help='The model to use for generating summary')
    parser.add_argument('-p', '--prompt', default='v1')
    parser.add_argument('-n', '--news_count', type=int, default=15, help='The number of news articles to retrieve')
    parser.add_argument('--home_url', type=str, default='https://www.reuters.com/business/', help='The home URL to retrieve news from') 
    parser.add_argument('--llm_use_case', type=str, default='sum_reuters', help='The use case for the llm model')
    parser.add_argument('--boilerplate_threshold', type=int, default=3, help='The threshold for boilerplate content')
    parser.add_argument('--params', nargs='+', type=dict_item_converter, default=[], help='Parameters for the online retriever')
    parser.add_argument('-q', '--quiet', action='store_true', default=False, help='静默模式，只显示错误信息（不显示进度和结果）')

    args = parser.parse_args()

    logger = logutils.SumLogger(quiet=args.quiet)

    try:
        model_id = llm.get_model(args.model)
    except ValueError as e:
        logger.error('模型错误: %s', e)
        sys.exit(1)
    home_retriever = oc.get_online_retriever(
        'crawl4ai',
        parser='link_extractor',
        link_extractor='//a[@data-testid="Heading"] | (.//text())[0] | (.//@href)[0]',
        use_proxy=True,
        cache_expire=1)
    
    sub_retriever = oc.get_online_retriever(
        'crawl4ai',
        parser='markdown',
        use_proxy=True,
        strip_boilerplate=True,
        cache_expire=24*7,
        mean_delay='10',
        **dict(args.params))
    
    if args.prompt in candidate_prompts:
        prompt = candidate_prompts[args.prompt]
    else:
        prompt = args.prompt

    json_links = home_retriever.retrieve(args.home_url)
    items = json.loads(json_links)

    # 过滤掉短的链接
    items = [item for item in items if len(item['text']) > 25]
    for item in items:
        logger.info('%s %s', item["text"], item["url"])

    urls = [item['url'] for item in items]
    if len(urls) == 0:
        logger.info('No valid news link found in %s', args.home_url)
        sys.exit(1)

    if args.news_count > 0:
        urls = urls[:args.news_count]
        items = items[:args.news_count]

    articles_contents = list(sub_retriever.retrieve_many(urls))

    raw_contents = ''
    article_sep = '-' * 80
    for item, s in zip(items, articles_contents):
        if not s:
            continue

        if raw_contents:
            raw_contents += article_sep + '\n'

        raw_contents += f'({item["text"]})[{item["url"]}]\n'
        raw_contents += s + '\n'

    # 通过统计多篇文章中出现的相同的行数来判断是否是多余的内容
    contents = web_utils.remove_duplicated_lines(raw_contents, args.boilerplate_threshold, whitelist_prefixes=[article_sep])

    logger.info('开始使用模型%s进行分析...', model_id)

    message = llm.chat(prompt=prompt, contents=contents, model_id=model_id,
                       use_case=args.llm_use_case, save=True)
    logger.result(message)
