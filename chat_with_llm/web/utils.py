import collections

__all__ = ['url_to_site', 'remove_duplicated_lines', 'strip_boilerplate', 'extract_links_from_markdown']

def url_to_site(url):
    # 解析url, 返回网站的初级域名. 例如www.reddit.com和login.reddit.com都返回reddit.com
    url = url.replace('https://', '').replace('http://', '')
    parts = url.split('/')
    domain = parts[0]
    domain_parts = domain.split('.')
    
    top_level_domains = {'com', 'org', 'net', 'edu', 'gov', 'mil', 'int', 'vip', 'app', 'me', 'tv', 'co', 'io', 'ai', 'cc', 'info', 'biz', 'name', 'pro', 'top', 'xyz', 'site', 'online', 'store',
                         'cn', 'us', 'jp', 'uk', 'au', 'de', 'fr', 'ru', 'it', 'es', 'br', 'in', 'ca', 'kr', 'mx', 'nl', 'se', 'no', 'fi', 'dk', 'pl', 'tr', 'hu', 'cz', 'ro', 'gr', 'pt', 'il', 'ae',
                         'sa', 'hk', 'tw', 'sg', 'my', 'th', 'ph', 'vn', 'id', 'pk', 'bd', 'lk', 'np', 'np', 'kh', 'la', 'mm', 'mn', 'kh', 'kh'}
                         
    site_parts = []

    for i, part in enumerate(reversed(domain_parts)):
        if part in top_level_domains and i < 2:
            site_parts.append(part)
        else:
            site_parts.append(part)
            break

    return '.'.join(reversed(site_parts))

def extract_links_from_markdown(s):
    sb_lvl = 0 # square bracket level
    rb_lvl = 0 # round bracket level
    links = []

    link_start = None
    link_end = None
    link_text = None
    for p, c in enumerate(s):
        if c == '[':
            sb_lvl += 1
            if sb_lvl == 1:
                link_start = p
        elif c == ']':
            sb_lvl = max(0, sb_lvl - 1)
            if sb_lvl == 0 and link_start is not None:
                link_text = s[link_start+1:p]
        elif c == '(' and sb_lvl == 0 and rb_lvl == 0 and link_start is not None:
            rb_lvl += 1
        elif c == ')' and sb_lvl == 0 and rb_lvl == 1:
            link_end = p + 1
            links.append((link_start, link_end, link_text))
            link_start = None
            link_end = None
            link_text = None
            rb_lvl = 0

    return links

def strip_boilerplate(contents):
    # 网页中包含大量的链接. 在这里我们尝试去掉这些链接

    outputs = []
    lines = contents.split('\n')
    for l in lines:
        links = extract_links_from_markdown(l)
        link_length = sum([e-s for s, e, _ in links])
        if link_length > 0.9 * len(l):
            continue

        l2 = ''
        p = 0
        for s, e, t in links:
            l2 += l[p:s]
            l2 += t
            p = e
            
        l2 += l[p:]

        outputs.append(l2)

    return '\n'.join(outputs)

def remove_duplicated_lines(contents, threshold, whitelist_prefixes=[]):
    assert threshold > 1

    # 通过统计多篇文章中出现的相同的行数来判断是否是多余的内容
    line_duplicates_cnt = collections.defaultdict(list)
    lines = []
    for line in contents.split('\n'):
        if line.strip():
            lines.append(line)
            line_duplicates_cnt[line].append(len(lines) - 1)
        else:
            lines.append('')

    boilerplate_lines = set()
    for line, indices in line_duplicates_cnt.items():
        if len(indices) >= threshold and not any(line.startswith(prefix) for prefix in whitelist_prefixes):
            boilerplate_lines.update(indices)

    lines = [line for i, line in enumerate(lines) if i not in boilerplate_lines]

    # 将三个以上的空行替换为两个空行
    empty_lines = set()
    empty_line_start = -1
    for l_ind, l in enumerate(lines):
        if l:
            if empty_line_start >= 0 and l_ind - empty_line_start > 2:
                empty_lines.update(range(empty_line_start + 2, l_ind))

            empty_line_start = -1
        else:
            if empty_line_start < 0:
                empty_line_start = l_ind

    if empty_line_start >= 0 and len(lines) - empty_line_start > 2:
        empty_lines.update(range(empty_line_start + 2, len(lines)))

    lines = [line for i, line in enumerate(lines) if i not in empty_lines]

    contents = '\n'.join(lines)

    return contents