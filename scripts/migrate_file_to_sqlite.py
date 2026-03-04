import argparse
import sys

import fnmatch

from chat_with_llm import storage

VALID_STORAGE_TYPES = ['chat_history', 'web_cache', 'subtitle_cache', 'video_summary', 'browser_state']

def migrate(storage_type, identifier, pattern, mode, dry_run=False, src=None, dst=None):
    if src is None:
        src = storage.get_storage(storage_type, identifier, storage_class='file')
    if dst is None:
        dst = storage.get_storage(storage_type, identifier, storage_class='sqlite')

    src_keys = {k for k in src.list() if fnmatch.fnmatch(k, pattern)}
    dst_keys = {k for k in dst.list() if fnmatch.fnmatch(k, pattern)}

    to_add = src_keys - dst_keys
    to_update = src_keys & dst_keys
    to_delete = dst_keys - src_keys

    added = 0
    updated = 0
    deleted = 0
    skipped = 0

    # 添加新 key
    for key in sorted(to_add):
        if dry_run:
            print(f'  [add] {key}')
        else:
            data = src.load_bytes(key)
            if data is not None:
                dst.save(key, data)
        added += 1

    # 处理已存在的 key
    for key in sorted(to_update):
        if mode == 'skip':
            skipped += 1
        elif mode == 'update' or mode == 'sync':
            if dry_run:
                print(f'  [update] {key}')
            else:
                data = src.load_bytes(key)
                if data is not None:
                    dst.save(key, data)
            updated += 1

    # 同步模式: 删除 sqlite 中多余的 key
    if mode == 'sync':
        for key in sorted(to_delete):
            if dry_run:
                print(f'  [delete] {key}')
            else:
                dst.delete(key)
            deleted += 1

    return added, updated, deleted, skipped


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='将 file storage 中的内容导入 sqlite storage'
    )
    parser.add_argument(
        'storage_type',
        choices=VALID_STORAGE_TYPES,
        help='存储类型'
    )
    parser.add_argument(
        'identifier',
        help='存储 identifier (如 sum_hn, sum_xwlb). 使用 _all 表示该类型下所有 identifier'
    )
    parser.add_argument(
        '-m', '--mode',
        choices=['skip', 'update', 'sync'],
        default='skip',
        help='skip: 忽略已存在的 key; update: 更新已存在的 key; sync: 完全同步 (会删除多余的 key). 默认 skip'
    )
    parser.add_argument(
        '--pattern',
        default='*',
        help='Only migrate key with this pattern.'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预览模式, 不实际执行'
    )

    args = parser.parse_args()

    from chat_with_llm import config
    import os

    storage_base = config.get('STORAGE_BASE_DIR')
    type_dir = os.path.join(storage_base, args.storage_type)

    if args.identifier == '_all':
        if not os.path.exists(type_dir):
            print(f'目录不存在: {type_dir}')
            sys.exit(1)
        identifiers = [d for d in os.listdir(type_dir) if os.path.isdir(os.path.join(type_dir, d))]
        identifiers.sort()
    else:
        identifiers = [args.identifier]

    if not identifiers:
        print('没有找到任何 identifier')
        sys.exit(1)

    total_added = 0
    total_updated = 0
    total_deleted = 0
    total_skipped = 0

    for ident in identifiers:
        prefix = f'[{args.storage_type}/{ident}]'
        if args.dry_run:
            print(f'{prefix} (dry-run, mode={args.mode})')
        else:
            print(f'{prefix} (mode={args.mode})')

        added, updated, deleted, skipped = migrate(
            args.storage_type, ident, args.pattern, args.mode, args.dry_run
        )

        print(f'{prefix} added={added}, updated={updated}, deleted={deleted}, skipped={skipped}')
        total_added += added
        total_updated += updated
        total_deleted += deleted
        total_skipped += skipped

    if len(identifiers) > 1:
        print(f'\n总计: added={total_added}, updated={total_updated}, deleted={total_deleted}, skipped={total_skipped}')
