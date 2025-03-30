import os.path
import time

from openai import OpenAI, OpenAIError

from chat_with_llm import config
from chat_with_llm import storage

CUR_DIR = os.path.dirname(os.path.abspath(__file__))

__all__ = ['get_model', 'get_storage', 'get_model_query_delay', 'chat', 'reason']

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
    'ds-reasoner': 'deepseek-reasoner-alpha-data-process',
    'ds-chat': 'deepseek-chat-alpha-data-process',
    'doubao-1.5-pro': 'doubao-1.5-pro-256k-250115',
    'abab6.5': 'abab6.5s-chat',
}

models_aliases = {v: k for k, v in models.items()}

model_query_delays = {
    'gemini-2.0-pro': 7,
    'gemini-2.0-flash-thinking': 7,
}

def get_model(simple_name, fail_on_unknown=True):
    if fail_on_unknown:
        if simple_name not in models and simple_name not in set(models.values()):
            raise ValueError(f'Unknown model name {simple_name}')
        
    model_id = models.get(simple_name, simple_name)
    if model_id == '':
        model_id = simple_name # 重命名为空表示使用原始名称

    return model_id

llm_storages = {}
def get_storage(use_case):
    if use_case not in llm_storages:
        llm_storages[use_case] = storage.get_storage('chat_history', use_case)
    
    return llm_storages[use_case]

def get_model_query_delay(model_id_or_alias):
    return model_query_delays.get(model_id_or_alias, None) or model_query_delays.get(models_aliases.get(model_id_or_alias, ''), 0)

def chat(prompt, contents, model_id, use_case='default', save=True, sep='\n', prompt_follow_contents=False, retries=3, throw_ex=True):
    response, reasoning = chat_impl(prompt, contents, model_id,
                                    use_case=use_case, save=save, sep=sep,
                                    prompt_follow_contents=prompt_follow_contents,
                                    retries=retries, throw_ex=throw_ex)
    return response

def reason(prompt, contents, model_id, use_case='default', save=True, sep='\n', prompt_follow_contents=False, retries=3, throw_ex=True):
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
                print(ex)
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
        storage = get_storage(use_case)

        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f'{timestamp}_{model_id.replace("/", "_").replace(":", "_")}.txt'
        while storage.has(filename):
            if filename.endswith(f'{model_id}.txt'):
                filename = filename[:-len('.txt')] + '_1.txt'
            else:
                filename_parts = filename.split('_')
                filename = '_'.join(filename_parts[:-1]) + f'_{int(filename_parts[-1]) + 1}.txt'

        data = f'model: {model_id}\n'
        data += f'prompt:\n{prompt}\n'
        data += f'reasoning:\n{reasoning}\n' if reasoning else ''
        data += f'response:\n{response}\n'

        storage.save(filename, data)
        storage.save(filename[:-len('.txt')] + '.input.txt', contents)
                                                                  
    return response, reasoning