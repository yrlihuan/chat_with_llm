import re
import json

from chat_with_llm.web import online_content
from chat_with_llm.web import c4ai

# hackernews评论
# 网址: https://news.ycombinator.com/item?id=<id>

class HNComments(c4ai.Crawl4AI):
    NAME = 'hn_comments'
    DESCRIPTION = 'Hackernews评论'
    HOME_URL = 'https://news.ycombinator.com/'

    def __init__(self, **params):
        params = {
            'name': HNComments.NAME,
            'description': HNComments.DESCRIPTION,
            'parser': 'markdown',
            'use_proxy': True,
            'strip_boilerplate': False,
            'mean_delay': '3',
            **params,
        }

        super().__init__(**params)
        
    def url2id(self, url):
        pattern = re.compile(r'https://news\.ycombinator\.com/item\?id=(\d+)')
        match = pattern.match(url)
        if not match:
            raise RuntimeError(f'Expect url to start with https://news.ycombinator.com/item?id=, got {url}')
        
        return match.group(1)
    
    def id2url(self, site_id):
        if not site_id.isdigit():
            raise RuntimeError('Expect site_id to be a number, got %s' % site_id)
        
        return f'https://news.ycombinator.com/item?id={site_id}'
    
    def list(self, n):
        hn_home_link_extractor = online_content.get_online_retriever(
            'crawl4ai',
            parser='link_extractor',
            link_extractor='//span[@class="subline"]/a[3]',
            use_proxy=True,
            cache_expire=1,
            force_fetch=False,
        )

        json_links = hn_home_link_extractor.retrieve(HNComments.HOME_URL)
        items = json.loads(json_links)

        # item is like
        # {
        #   "url": "https://news.ycombinator.com/item?id=43636568",
        #   "text": "16 comments" or "discuss",
        # }

        for item in items:
            text = item['text']
            if 'comment' in text:
                item['comments'] = int(text.split()[0])
            else:
                item['comments'] = 0
                
        items.sort(key=lambda x: (x['comments'], x['url']), reverse=True)
        items = items[:min(n, len(items))]
        return [items['url'] for items in items]

    def parse(self, url, raw):
        def update_and_get_level(comments, comment_id):
            info = comments.get(comment_id)
            if not info:
                return 0
            
            level = info.get('level')
            if level is not None:
                return level
            
            parent_id = info.get('parent_id')
            if not parent_id:
                level = 0
            else:
                level = update_and_get_level(comments, parent_id) + 1

            info['level'] = level
            return level
        
        md = super().parse(url, raw)

        # example:
        #
        # | ![](https://news.ycombinator.com/s.gif)|  [](https://news.ycombinator.com/vote?id=43633751&how=up&goto=item%3Fid%3D43631543) |  [gorfian_robot](https://news.ycombinator.com/user?id=gorfian_robot) [13 hours ago](https://news.ycombinator.com/item?id=43633751) | [prev](https://news.ycombinator.com/item?id=43631543#43634381) | [next](https://news.ycombinator.com/item?id=43631543#43638079) [[–]](javascript:void\(0\))
        # Nike doesn't sell shoes. Those are a loss leader. They sell you brand and lifestyle bullshit at a very high markup. _[reply](https://news.ycombinator.com/reply?id=43633751&goto=item%3Fid%3D43631543%2343633751)_
        # ---|---|---
        # | ![](https://news.ycombinator.com/s.gif)|  [](https://news.ycombinator.com/vote?id=43633769&how=up&goto=item%3Fid%3D43631543) |  [reed1234](https://news.ycombinator.com/user?id=reed1234) [13 hours ago](https://news.ycombinator.com/item?id=43633769) | [parent](https://news.ycombinator.com/item?id=43631543#43633751) | [next](https://news.ycombinator.com/item?id=43631543#43634705) [[–]](javascript:void\(0\))
        # "In fiscal 2024, footwear accounted for 68 percent of Nike's total revenues." [https://www.statista.com/statistics/412760/nike-global-reven...](https://www.statista.com/statistics/412760/nike-global-revenue-share-by-product/) _[reply](https://news.ycombinator.com/reply?id=43633769&goto=item%3Fid%3D43631543%2343633769)_
        # ---|---|---
        # | ![](https://news.ycombinator.com/s.gif)|  [](https://news.ycombinator.com/vote?id=43633842&how=up&goto=item%3Fid%3D43631543) |  [echoangle](https://news.ycombinator.com/user?id=echoangle) [13 hours ago](https://news.ycombinator.com/item?id=43633842) | [root](https://news.ycombinator.com/item?id=43631543#43633751) | [parent](https://news.ycombinator.com/item?id=43631543#43633769) | [next](https://news.ycombinator.com/item?id=43631543#43634705) [[–]](javascript:void\(0\))
        # Revenue doesn't really show they are not loss leaders. Profit would be more useful. _[reply](https://news.ycombinator.com/reply?id=43633842&goto=item%3Fid%3D43631543%2343633842)_
        # ---|---|---

        # 从markdown中parse出评论的作者, 评论的树结构, 以及评论的内容
        comments = {}
        info = {}
        #print('\n'.join(md.split('\n')[:8]))

        for l in md.split('\n'):
            if 'https://news.ycombinator.com/vote' in l:
                # parse出行内的链接
                link_pattren = re.compile(r'\[(.*?)\]\((.*?)\)')
                matches = link_pattren.findall(l)
                links = [(match[0], match[1].replace('https://news.ycombinator.com/', '')) for match in matches]

                # [](s.gif) | [](vote?id=43639581&how=up&goto=item%3Fid%3D43631543) | [neonate](user?id=neonate) | [5 hours ago](item?id=43639581) | [next](item?id=43631543#43632822) | [[–]](javascript:void\(0\)
                info = {}
                for text, link in links:
                    if link.startswith('vote?id='):
                        # 取出评论id
                        info['comment_id'] = link.split('=')[1].split('&')[0]
                        if info['comment_id'] == self.url2id(url):
                            info['origin_post'] = True

                    elif link.startswith('user?id='):
                        # 取出用户
                        info['user_id'] = link.split('=')[1]
                    elif text == 'parent':
                        # parent link is like: item?id=43631543#43633751
                        info['parent_id'] = link.split('=')[1].split('#')[1]
                    elif info.get('origin_post') and text and link and not info.get('post_title'):
                        info['post_title'] = text
                        info['post_url'] = link

                comment_id = info.get('comment_id')
                if not comment_id:
                    continue

                info['seq'] = len(comments)
                comments[comment_id] = info
            else:
                reply_link_prefix = '_[reply](https://news.ycombinator.com/reply?'
                reply_link_start = l.find(reply_link_prefix)
                if reply_link_start > 0 and not info.get('origin_post'):
                    info['text'] = l[:reply_link_start-1]
        
        #print(comments.get(self.url2id(url)))
        for commend_id in comments:
            update_and_get_level(comments, commend_id)

        contents = ''
        comments = sorted(comments.values(), key=lambda info: info['seq'])
        for info in comments:
            contents += '  ' * info['level']
            if info.get('parent_id'):
                reply_to = f", reply to {info.get('parent_id', 0)}"
            else:
                reply_to = ''
            
            if info.get('post_title'):
                contents += f"**[{info['post_title']}]({info['post_url']})**\n"
            else:
                contents += f"id: {info['comment_id']} (by {info['user_id']}{reply_to}): {info.get('text', '')}\n"
        
        return contents

online_content.add_online_retriever(HNComments.NAME, HNComments)