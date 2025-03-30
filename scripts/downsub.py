import requests
import os.path
import yaml

from chat_with_llm import config

CURDIR = os.path.dirname(os.path.abspath(__file__))

def retrive_metadata(url):
    api_url = 'https://api.downsub.com/download'
    headers = {
        'Authorization': f'Bearer {config.get("DOWNSUB_API_KEY")}',
        'Content-Type': 'application/json'
    }   
    data = {
        'url': url,
    }

    response = requests.post(api_url, headers=headers, json=data)
    data = response.json()
    return data

def retrive_subtitles(metadata):
#    print(metadata.keys())

    print('Valid langs: ' + ', '.join([sub['language'] for sub in metadata['data']['subtitles']]))

    support_langs = {
        'chinese': 'chinese',
        'chinese (simplified)': 'chinese',
        'chinese (traditional)': 'chinese',
        'english': 'english',
        'japanese': 'japanese',
        'korean': 'korean',
        'french': 'french',
        'english (united states)': 'english',
        'english (united kingdom)': 'english',
        'english (australian)': 'english',
        'english (canadian)': 'english',
        'english (great britain)': 'english',

        'chinese (auto-generated)': 'chinese_auto',
        'english (auto-generated)': 'english_auto',
        'japanese (auto-generated)': 'japanese_auto',
        'korean (auto-generated)': 'korean_auto',
        'french (auto-generated)': 'french_auto',
    }

    subs = []
    for sub in metadata['data']['subtitles']:
        lang = sub['language'].lower()
        if lang not in support_langs:
            continue

        lang_short = support_langs[lang]
        if lang_short in [s[0] for s in subs]:
            continue

        for fmt in sub['formats']:
            if fmt['format'] == 'txt' or fmt['format'] == 'srt':
                url = fmt['url']
                try:
                    contents = requests.get(url).text
                    subs.append((lang_short, fmt['format'], contents))
                except Exception as e:
                    print(f'Error retriving subtitles: {e}')

    return subs

if __name__ == '__main__':
    url = 'https://www.youtube.com/watch?v=_1f-o0nqpEI'
    metadata = retrive_metadata(url)
    response = retrive_subtitles(metadata)

