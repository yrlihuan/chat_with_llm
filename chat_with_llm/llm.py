import os.path
import time

from openai import OpenAI, OpenAIError

from chat_with_llm import config

CUR_DIR = os.path.dirname(os.path.abspath(__file__))

__all__ = ['get_model', 'get_save_path', 'get_model_query_delay', 'chat', 'reason']

models = {
    '4o': 'or-openai/chatgpt-4o-latest',
    'o1': 'lobechat-o1-2024-12-17',
    'o1-mini': 'or-openai/o1-mini-2024-09-12',
    'o3-mini': 'lobechat-o3-mini-2025-01-31',
    'gpt4.5': 'or-openai/gpt-4.5-preview-2025-02-27',
    'gpt-4.5': 'or-openai/gpt-4.5-preview-2025-02-27',
    'gemini-1.5-pro': '',
    'gemini-2.0-flash': '',
    'gemini-2.0-flash-thinking': 'gemini-2.0-flash-thinking-exp-01-21',
    'gemini-2.0-pro': 'gemini-2.0-pro-exp-02-05',
    'grok-2.0-pro': '',
    'grok-2.0-latest': '',
    'grok-beta': '',
    'claude-3.7': 'claude-3-7-sonnet-20250219',
    'deepseek-reasoner': 'deepseek-reasoner-alpha-data-process',
    'deepseek-chat': 'deepseek-chat-alpha-data-process',
}

models_aliases = {v: k for k, v in models.items()}

model_query_delays = {
    'gemini-2.0-pro': 7,
    'gemini-2.0-flash-thinking': 7,
}

def get_model(simple_name):
    model_id = models.get(simple_name, simple_name)
    if model_id == '':
        model_id = simple_name # 重命名为空表示使用原始名称

    return model_id

def get_save_path(use_case):
    path = os.path.join(config.get('CHAT_HISTORY_DIR'), use_case)
    return path

def get_model_query_delay(model_id_or_alias):
    return model_query_delays.get(model_id_or_alias, None) or model_query_delays.get(models_aliases.get(model_id_or_alias, ''), 0)

def chat(prompt, contents, model_id, use_case='default', save=True, sep='\n', prompt_follow_contents=False, retries=10, throw_ex=True):
    response, reasoning = chat_impl(prompt, contents, model_id,
                                    use_case=use_case, save=save, sep=sep,
                                    prompt_follow_contents=prompt_follow_contents,
                                    retries=retries, throw_ex=throw_ex)
    return response

def reason(prompt, contents, model_id, use_case='default', save=True, sep='\n', prompt_follow_contents=False, retries=10, throw_ex=True):
    response, reasoning = chat_impl(prompt, contents, model_id,
                                    use_case=use_case, save=save, sep=sep,
                                    prompt_follow_contents=prompt_follow_contents,
                                    retries=retries, throw_ex=throw_ex)
    return response, reasoning

def chat_impl(prompt, contents, model_id, use_case, save, sep, prompt_follow_contents, retries, throw_ex):
    client = OpenAI(
        api_key=config.get("OPENAI_API_KEY"),
        base_url=config.get('OPENAI_API_BASE'),
    )

    request_message = f'{prompt}{sep}{contents}' if not prompt_follow_contents else f'{contents}{sep}{prompt}'
    chat_completion = None
    retry_cnt = 0
    while chat_completion is None:
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": request_message,
                    }
                ],
                model=model_id,
            )
        except OpenAIError as ex:
            if retry_cnt < retries:
                print('openai api failed, retrying...')
                time.sleep(min(5 * retry_cnt, 60))
                retry_cnt += 1
                continue
            else:
                print('openai api failed, giving up')
                print('input_len: ', len(prompt), len(contents))
                print(prompt)
                print(contents[:min(256, len(contents))])

                if throw_ex:
                    raise ex
                else:
                    return None, None

    response = chat_completion.choices[0].message.content

    if 'reasoning_content' in chat_completion.choices[0].message:
        reasoning = chat_completion.choices[0].message.reasoning_content
    else:
        reasoning = None

    if save:
        use_case_dir = get_save_path(use_case)
        if not os.path.exists(use_case_dir):
            os.makedirs(use_case_dir)

        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f'{use_case_dir}/{timestamp}_{model_id.replace("/", "_").replace(":", "_")}.txt'
        while os.path.exists(filename):
            if filename.endswith(f'{model_id}.txt'):
                filename = filename[:-len('.txt')] + '_1.txt'
            else:
                filename_parts = filename.split('_')
                filename = '_'.join(filename_parts[:-1]) + f'_{int(filename_parts[-1]) + 1}.txt'

        data = f'model: {model_id}\n'
        data += f'prompt:\n{prompt}\n'
        data += f'reasoning:\n{reasoning}\n' if reasoning else ''
        data += f'response:\n{response}\n'

        with open(filename, 'w') as fout:
            fout.write(data)

        with open(filename[:-len('.txt')] + '.input.txt', 'w') as fout:
            fout.write(contents)
                                                                  
    return response, reasoning