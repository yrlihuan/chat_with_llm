import sys
import argparse
import time

from tqdm import tqdm

from chat_with_llm import llm
from chat_with_llm.web import online_content as oc


if __name__ == "__main__":
    dict_item_converter = lambda s: tuple([s[:s.index('=')], s[s.index('=')+1:]]) if '=' in s else (s, None)

    parser = argparse.ArgumentParser(description='读取hackernews的评论链接, 总结各方观点.')

    candidate_prompts = {
        'v1': '下面是hackernews上面的文章以及hackernews用户针对文章进行的讨论. 前面是文章的内容(有可能缺失), '
              '然后用长==连线分割, 后面是hackernews的评论. 如果存在文章链接, 请先输出"## [文章标题](文章链接)". '
              '然后总结评论中出现的观点, 请同时将持有不同观点的用户也标注出来. 使用中文, 不限字数.',

        'v2': '下面是hackernews上面的文章以及hackernews用户针对文章进行的讨论. 前面是文章链接和评论链接, 然后是文章的内容(有可能缺失).'
              '用长==连线分割后, 是hackernews的评论. 请先输出"## [文章标题](文章链接)  ([HN评论](评论链接))". '
              '接下来简单总结文章的内容, 然后总结评论中出现热门观点(附带发言者nickname). '
              '"文章"和"评论"的标题使用三级标签(h3). 使用中文, 不限字数.',

        'v3': '下面是hackernews上面的文章以及hackernews用户针对文章进行的讨论. 前面是文章链接和评论链接, 然后是文章的内容(有可能缺失).'
              '用长==连线分割后, 是hackernews的评论. 请先输出"## [文章标题](文章链接)  ([HN评论](评论链接))". '
              '接下来简单总结文章的内容, 然后总结评论中出现热门观点, 并将热门观点的关键词转化为链接(地址: https://news.ycombinator.com/item?id=<id>). '
              '"文章"和"评论"的标题使用三级标签(h3). 使用中文, 不限字数.',

        'v4': '下面是hackernews上面的文章以及hackernews用户针对文章进行的讨论. 前面是文章链接和评论链接, 然后是文章的内容(有可能缺失).'
              '用长==连线分割后, 是hackernews的评论. 请先输出"## [文章标题](文章链接)  ([HN评论](评论链接))". '
              '接下来简单总结文章的内容, 然后总结评论中出现热门观点, 并将热门观点的关键词转化为链接(地址: https://news.ycombinator.com/item?id=<id>). '
              '"文章"和"评论"的标题使用三级标签(h3). 使用中文, 不限字数. '
              '下面是一个输出的格式的例子: '
              '*   部分评论者认同文章观点，觉得《黑镜》的[持续悲观缺乏细微差别](https://news.ycombinator.com/item?id=43649154)，让人感觉扁平，尤其是后期剧集。'
    }

    parser.add_argument('-c', '--comment_id', type=str, default=None, help='The home URL to retrieve news from')
    parser.add_argument('-p', '--prompt', default='v3')

    parser.add_argument('-m', '--model', type=str, default='gemini-2.0-pro', help='The model to use for generating summary')

    parser.add_argument('--llm_use_case', type=str, default='sum_hn_comments', help='The use case for the llm model')
    parser.add_argument('--model_alt', default='gemini-2.0-pro', help='The alternative model to use for generating summary')
    parser.add_argument('--model_alt_threshold', default=256*1024, type=int, help='The threshold to use the alternative model')
    parser.add_argument('--daily_topn', type=int, default=10, help='The number of daily top articles to retrieve')
    parser.add_argument('--skip_processed', action='store_true', default=False, help='Skip processed articles')
    parser.add_argument('--params', nargs='+', type=dict_item_converter, default=[], help='Parameters for the online retriever')

    args = parser.parse_args()

    model_id = llm.get_model(args.model)
    model_id_alt = llm.get_model(args.model_alt)

    params = dict(args.params)

    hn_retriever = oc.get_online_retriever(
        'hn_comments', cache_expire=1, **params)
    
    if args.prompt in candidate_prompts:
        prompt = candidate_prompts[args.prompt]
    else:
        prompt = args.prompt

    if args.comment_id:
        url, site_id = hn_retriever.parse_url_id(args.comment_id)
        urls = [url]
    else:
        urls = hn_retriever.list(n=args.daily_topn)

        if args.skip_processed:
            processed_urls = set()

            # 读取最近的聊天记录, 检查该文章是否已经被处理过
            chat_history_storage = llm.get_storage(args.llm_use_case)
            files = chat_history_storage.list()
            files.sort(reversed=True)

            date_lookback = 1
            date_lookback_str = time.strftime('%Y%m%d_%H%M%S', time.localtime(time.time() - date_lookback * 24 * 3600))

            for file in files:
                if file.endswith('.input.txt') or file.endswith('.summary.txt'):
                    continue

                # filename is in format: YYMMDD_HHMMSS_<identifier>.txt
                time_str = '_'.join(file.split('_')[:2])
                if time_str < date_lookback_str:
                    break

                chat_contents = chat_history_storage.load(file)
                for url in urls:
                    if url in chat_contents:
                        processed_urls.add(url)

            urls = [url for url in urls if url not in processed_urls]

    # 获取评论
    article_comments = hn_retriever.retrieve_many(urls)
    article_urls = []
    for article_seq, (url, comments) in enumerate(zip(urls, article_comments)):
        if not comments:
            print(f'Failed to retrieve comments for {url}')
            continue

        first_eol = comments.find('\n')
        if first_eol < 0:
            continue

        first_line = comments[:first_eol]

        pos_url_start = first_line.find('(http')
        if pos_url_start < 0:
            continue

        pos_url_end = first_line.find(')', pos_url_start)
        url = first_line[pos_url_start+1:pos_url_end]
        article_urls.append((article_seq, url))

    # 尝试获取文章的原文
    article_contents = {}
    if len(article_urls):
        c4ai_retriever = oc.get_online_retriever(
            'crawl4ai',
            strip_boilerplate=True,
            use_proxy=True,
            cache_expire=24*7,
            **params)
        
        articles = c4ai_retriever.retrieve_many([url for _, url in article_urls])
        for (article_seq, url), content in zip(article_urls, articles):
            if not content:
                continue

            # 文章的原文
            article_contents[article_seq] = content

    article_urls = dict(article_urls)

    for seq, (comment_url, comments) in tqdm(enumerate(zip(urls, article_comments))):
        contents = ''

        url = article_urls.get(seq)
        article = article_contents.get(seq)
        
        contents += f'article url: {url}\n' if url else ''
        contents += f'comment url: {comment_url}\n\n'
        contents += ('artitle:\n' + article + '\n') if article else ''
        contents += '=' * 80 + '\n'

        contents += comments + '\n'

        model_to_use = model_id
        if len(contents) > args.model_alt_threshold:
            # 如果内容过长, 使用更大的模型
            model_to_use = model_id_alt

        message, reasoning, filename = llm.chat_impl(
            prompt=prompt,
            contents=contents,
            model_id=model_to_use,
            use_case=args.llm_use_case,
            save=True)
        
        if seq == 0:
            print(contents)
            print(message)
