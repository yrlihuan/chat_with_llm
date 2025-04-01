import sys
import time
import os.path
import argparse

from tqdm import tqdm

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from chat_with_llm import llm
from chat_with_llm.web import online_content as oc

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Analyze xwlb news using llm.')

    last_day = time.strftime('%Y%m%d', time.localtime(time.time() - 86400))
    parser.add_argument('-d', '--date', default=last_day, help='The last date to analyze')
    parser.add_argument('-n', type=int, default=1, help='Contain at most n days of news')
    parser.add_argument('-s', '--step', type=int, default=1, help='Pick news from every n days')
    parser.add_argument('-m', '--model', type=str, default='ds-chat', help='The model to use for generating summary')
    parser.add_argument('-p', '--prompt', default='v2')
    parser.add_argument('--use_news_date', type=lambda s: s.lower() == 'true' or s == '1', default=False, help='Whether to use the date of the news')
    parser.add_argument('--prompt_follow_contents', type=lambda s: s.lower() == 'true' or s == '1', default=False, help='Whether to follow the contents after the prompt')
    parser.add_argument('--llm_use_case', type=str, default='sum_xwlb', help='The use case for the llm model')

    args = parser.parse_args()

    model_id = llm.get_model(args.model)

    prompts = {
        'v1': f'下面是中央电视台新闻联播的内容。将新闻中除了政治领域以外的和以往不同的表述(不要从文章中推断，而是使用已有的知识)总结一下。尽量简短。',
        'v2': f'下面是中央电视台新闻联播的内容。将新闻中除了政治领域以外的内容总结一下。尽量剪短, 如果有重要的信息, 请突出出来。',
    }

    if args.prompt in prompts:
        prompt = prompts[args.prompt]
    else:
        prompt = args.prompt

    retriever = oc.get_online_retriever('mrxwlb', date_end=args.date)
    urls = retriever.list(args.n * args.step)
    
    outputs = ''
    outputs += prompt + '\n\n'

    cur_date = time.strftime('%Y%m%d', time.localtime())
    for url in tqdm(urls[args.step-1::args.step]):
        key_date = retriever.url2id(url)
        contents = ''
        
        parsed = retriever.retrieve(url)
        if parsed:
            contents += f'{key_date}日新闻联播\n\n{parsed}\n'
        else:
            print(f'Retrieving {key_date} failed.')
            continue

        save_date = key_date if cur_date != key_date and args.use_news_date else None
        message = llm.chat(
            prompt=prompt, contents=contents, model_id=model_id,
            use_case=args.llm_use_case, save=True, save_date=save_date,
            prompt_follow_contents=args.prompt_follow_contents,
            retries=3, throw_ex=False)
        
        if not message:
            print(f'Analyze {key_date} failed. Skip this date.')
            continue
        
        outputs += f'{key_date}\n{message}\n\n'

        delay = llm.get_model_query_delay(args.model)
        if delay:
            time.sleep(delay)
    
    