import sys
import argparse

from tqdm import tqdm

from chat_with_llm import llm
from chat_with_llm.web import online_content as oc


if __name__ == "__main__":
    dict_item_converter = lambda s: tuple([s[:s.index('=')], s[s.index('=')+1:]]) if '=' in s else (s, None)

    parser = argparse.ArgumentParser(description='读取hackernews的评论链接, 总结各方观点.')

    candidate_prompts = {
        'v1': '下面是hackernews上面的文章以及hackernews用户针对文章进行的讨论. 前面是文章的内容(有可能缺失), 然后用长==连线分割, 后面是hackernews的评论. 如果存在文章链接, 请先输出[文章标题](文章链接). 然后总结评论中出现的观点, 请同时将持有不同观点的用户也标注出来. 使用中文, 不限字数.',
    }

    parser.add_argument('-m', '--model', type=str, default='ds-chat', help='The model to use for generating summary')
    parser.add_argument('--model_alt', default='gemini-2.0-pro', help='The alternative model to use for generating summary')
    parser.add_argument('-p', '--prompt', default='v1')
    parser.add_argument('--comment_id', type=str, default=None, help='The home URL to retrieve news from')
    parser.add_argument('--daily_topn', type=int, default=10)
    parser.add_argument('--llm_use_case', type=str, default='sum_hn_comments', help='The use case for the llm model')
    parser.add_argument('--params', nargs='+', type=dict_item_converter, default=[], help='Parameters for the online retriever')

    args = parser.parse_args()

    model_id = llm.get_model(args.model)
    model_id_alt = llm.get_model(args.model_alt)

    hn_retriever = oc.get_online_retriever(
        'hn_comments', cache_expire=1)
    
    if args.prompt in candidate_prompts:
        prompt = candidate_prompts[args.prompt]
    else:
        prompt = args.prompt

    if args.comment_id:
        url, site_id = hn_retriever.parse_url_id(args.comment_id)
        urls = [url]
    else:
        urls = hn_retriever.list(n=args.daily_topn)

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

        pos_http = first_line.find('http')
        if pos_http < 0:
            continue

        url = first_line[pos_http:]
        article_urls.append((article_seq, url))

    # 尝试获取文章的原文
    article_contents = {}
    if len(article_urls):
        c4ai_retriever = oc.get_online_retriever(
            'crawl4ai',
            strip_boilerplate=True,
            use_proxy=True,
            cache_expire=24*7)
        
        articles = c4ai_retriever.retrieve_many([url for _, url in article_urls])
        for (article_seq, url), content in zip(article_urls, articles):
            if not content:
                continue

            # 文章的原文
            article_contents[article_seq] = content

    article_urls = dict(article_urls)

    for seq, comments in tqdm(enumerate(article_comments)):
        contents = ''

        url = article_urls.get(seq)
        article = article_contents.get(seq)
        
        contents += f'article url: {url}\n' if url else ''
        contents += article + '\n' if article else ''
        contents += '=' * 80 + '\n'

        contents += comments + '\n'

        model_to_use = model_id
        if len(contents) > 128 * 1024:
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
