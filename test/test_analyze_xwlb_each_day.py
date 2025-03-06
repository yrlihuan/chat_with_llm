import sys
import time
import os.path
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import llm
from web import online_content as oc

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze xwlb news using llm.')

    parser.add_argument('-d', '--date', default='20250303', help='The last date to analyze')
    parser.add_argument('-s', '--step', type=int, default=20, help='Pick news from every n days')
    parser.add_argument('-n', type=int, default=12, help='Contain at most news from the last n days')
    parser.add_argument('-m', '--model', type=str, default='gemini-2.0-pro', help='The model to use for generating summary')
    parser.add_argument('-p', '--prompt', default=f'下一行之后是中央电视台新闻联播的内容。将新闻中除了政治领域以外的和以往不同的表述(不要从文章中推断，而是使用已有的知识)总结一下。尽量简短，只包括最重要的一两点。')
    parser.add_argument('--prompt_follow_contents', type=lambda s: s.lower() == 'true' or s == '1', default=False, help='Whether to follow the contents after the prompt')
    parser.add_argument('--llm_use_case', type=str, default='xwlb_each_day', help='The use case for the llm model')

    args = parser.parse_args()

    model_id = llm.get_model(args.model)
    retriever = oc.get_online_retriever('mrxwlb')
    urls = retriever.list(args.n * args.step, date_end=args.date)
    
    outputs = ''
    outputs += args.prompt + '\n\n'

    prompt = args.prompt
    for url in urls[args.step-1::args.step]:
        key_date = retriever.url2id(url)
        parsed = retriever.retrieve(url, force_fetch=False, force_parse=False, update_cache=True)
        if parsed:
            if url == urls[-1]:
                contents += '-' * 80 + '\n'

            contents = f'{key_date}日新闻联播文字版\n{parsed}\n'
        else:
            print(f'Retrieving {key_date} failed')
            continue

        message = llm.chat(
            prompt=prompt, contents=contents, model_id=model_id,
            use_case=args.llm_use_case, save=False,
            prompt_follow_contents=args.prompt_follow_contents,
            retries=20)
        
        outputs += f'{key_date}\n{message}\n\n'

        delay = llm.get_model_query_delay(args.model)
        if delay:
            time.sleep(delay)

    output_dir = llm.get_save_path(args.llm_use_case)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(outputs)
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    filename = f'{timestamp}_{model_id}_{args.date}_{args.step}_{args.n}.txt'
    filename = filename.replace(':', '_').replace('/', '_')
    output_file = os.path.join(output_dir, filename)

    with open(output_file, 'w') as f:
        f.write(outputs)
    
    