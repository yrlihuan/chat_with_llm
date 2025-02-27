import requests
import os.path
import yaml

CURDIR = os.path.dirname(os.path.abspath(__file__))

def retrive_metadata(url):
    cfg = yaml.load(open(os.path.join(CURDIR, 'config.yaml')), yaml.FullLoader)

    api_url = 'https://api.downsub.com/download'
    headers = {
        'Authorization': f'Bearer {cfg["DOWNSUB_API_KEY"]}',
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

    subs = []
    for sub in metadata['data']['subtitles']:
        if not sub['language'].lower() == 'english' and not sub['language'].lower() == 'chinese':
            continue

        for fmt in sub['formats']:
            if fmt['format'] == 'txt':
                url = fmt['url']
                try:
                    contents = requests.get(url).text
                    subs.append((sub['language'], contents))
                except Exception as e:
                    print(f'Error retriving subtitles: {e}')

    return subs

if __name__ == '__main__':
    url = 'https://www.youtube.com/watch?v=_1f-o0nqpEI'
    metadata = retrive_metadata(url)
    response = retrive_subtitles(metadata)
    
                

