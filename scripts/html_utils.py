import os.path
import collections

__all__ = ['remove_duplicated_lines']

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