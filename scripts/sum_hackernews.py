import argparse
import re

from chat_with_llm import llm
from chat_with_llm.web import online_content as oc

def extract_articles(contents):
    # line is like:
    # 9. | [](https://news.ycombinator.com/vote?id=43339584&how=up&goto=news)| [Show HN: VSC – An open source 3D Rendering Engine in C++](https://github.com/WW92030-STORAGE/VSC)
    # ([github.com/ww92030-storage](https://news.ycombinator.com/from?site=github.com/ww92030-storage))
    #
    # 52 points by [NormalExisting](https://news.ycombinator.com/user?id=NormalExisting) [5 hours ago]
    # (https://news.ycombinator.com/item?id=43339584) | [hide](https://news.ycombinator.com/hide?id=43339584&goto=news) | [6 comments](https://news.ycombinator.com/item?id=43339584)

    articles = []
    seq_re = re.compile(r'^(\d+)\.')
    link_re = re.compile(r'\[([^]]*)\] *\((http[^)]*)\)')
    hn_id_re = re.compile(r'\?id=(\d+)')

    for line in contents.split('\n'):
        parts = line.split('|')

        base_ind = None
        seq = None
        hn_id = None
        title = None
        link = None
        comments = None
        comments_link = None
        for part_ind, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue

            seq_match = seq_re.match(part)
            if seq_match:
                seq = int(seq_match.group(1))
                base_ind = part_ind
                continue

            id_match = hn_id_re.search(part)
            if id_match:
                hn_id = id_match.group(1)

            # 如果匹配序号, 则说明是标题和链接
            if base_ind is not None and part_ind == base_ind + 2:
                m = link_re.match(part)
                if not m:
                    continue

                title = m.group(1)
                link = m.group(2)
            # 否则, 则对应是评论数和评论链接
            elif base_ind is None:
                m = link_re.match(part)
                if not m:
                    continue

                text = m.group(1)
                l = m.group(2)

                if ' ' in text and len(text.split(' ')) == 2 and text.split(' ')[1].startswith('comment'):
                    comments = int(text.split(' ')[0])
                    comments_link = l
                    break

        if title and hn_id:
            articles.append({
                'hn_id': hn_id,
                'seq': seq,
                'title': title,
                'link': link,
                'comments': comments,
                'comments_link': comments_link,
            })
        elif comments is not None and hn_id is not None:
            for item in articles:
                if item['hn_id'] == hn_id:
                    item['comments'] = comments
                    item['comments_link'] = comments_link

    return articles


import time
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Summarize hackernews daily posts.')

    candidate_prompts = {
        'v1': '以下是今天hackernews的文章. 文章之间用长--连线分割. 请根据内容以及每篇文章的评论数总结今天的热点, '
              '以及热点文章中的新颖观点. 输出中文, 不限字数, 可以列举多个热点。',
        'v2': '以下是今天hackernews的文章. 文章之间用长--连线分割. 请根据内容以及每篇文章的评论数以及你的理解, '
              '选取五到八篇最有新意和知识性的文章, 总结其观点. 每个文章输出的时候先输出[文章标题](链接)'
              '以及[评论数](评论链接). 输出中文, 不限字数. ',
    }

    parser.add_argument('-m', '--model', type=str, default='gemini-2.5-pro', help='The model to use for generating summary')
    parser.add_argument('-p', '--prompt', default='v2')
    parser.add_argument('-c', '--min_comments', type=int, default=30, help='Minimum number of comments to consider reading the article')
    parser.add_argument('-d', '--dedup_n', type=int, default=4, help='Remove duplicate articles from the last n runs.') 
    parser.add_argument('--llm_use_case', type=str, default='sum_hn', help='The use case for the llm model')

    args = parser.parse_args()

    model_id = llm.get_model(args.model)
    hn_retriever = oc.get_online_retriever('crawl4ai',
                                           strip_boilerplate=False,
                                           use_proxy=True,
                                           cache_expire=1,
                                           force_fetch=True)
    
    retriever = oc.get_online_retriever('crawl4ai',
                                        strip_boilerplate=True,
                                        use_proxy=True,
                                        cache_expire=24*7)
    
    if args.prompt in candidate_prompts:
        prompt = candidate_prompts[args.prompt]
    else:
        prompt = args.prompt

    contents = ''

    hn_url = 'https://news.ycombinator.com/news'
    hn_news = hn_retriever.retrieve(hn_url)
    
    articles = extract_articles(hn_news)

    articles = [article for article in articles if article['comments'] is not None and article['comments'] >= args.min_comments]

    chat_history_storage = llm.get_storage(args.llm_use_case)
    if args.dedup_n > 0:
        # 读取最近的聊天记录
        files = chat_history_storage.list()
        files = list(filter(lambda x: x.endswith('.input.txt'), files))
        files.sort(reverse=True)

        recent = files[:min(args.dedup_n, len(files))]

        for f in recent:
            recent_contents = chat_history_storage.load(f)
            articles = list(filter(lambda x: x['link'] not in recent_contents, articles))

    if len(articles) == 0:
        print(f'No articles found with at least {args.min_comments} comments')
        exit(1)

    articles_contents = list(retriever.retrieve_many([article['link'] for article in articles]))
    for item, s in zip(articles, articles_contents):
        item['content'] = s or ''

    # for article in articles:
    #     contents = f'{article["seq"]}. {article["hn_id"]}, {article["title"]} ({article["link"]}), {len(article["content"])}'
    #     if article['comments'] is not None:
    #         contents += f', {article["comments"]} comments ({article["comments_link"]})'

    #     print(contents)

    # 按评论数排序
    articles.sort(key=lambda x: -x['comments'])

    contents = ''
    for item in articles:
        if not item['content']:
            continue

        if contents:
            contents += '-' * 80 + '\n'

        contents += f'({item["title"]})[{item["link"]}]\n'
        contents += f'({item["comments"]} comments)[{item["comments_link"]}]\n'
        contents += item['content'] + '\n'

    print(f'共{len(articles)}篇文章如下:')
    for p, article in enumerate(articles):
        print(f'{article["title"]} ({article["link"]}) ({article["comments"]} comments)')

    print(f'开始使用模型{model_id}进行分析...\n')

    message = llm.chat(prompt=prompt, contents=contents, model_id=model_id,
                       use_case=args.llm_use_case, save=True)
    print(message)
