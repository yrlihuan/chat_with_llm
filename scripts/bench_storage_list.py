import argparse
import tempfile
import time
import os

from chat_with_llm.storage import ContentStorage_File, ContentStorage_Sqlite


def populate(file_s, sqlite_s, n):
    for i in range(n):
        key = f'{i:06d}.txt'
        value = f'content_{i}'
        file_s.save(key, value)
        sqlite_s.save(key, value)


def bench_list(storage, rounds):
    t0 = time.time()
    for _ in range(rounds):
        keys = storage.list()
    t1 = time.time()
    return t1 - t0, len(keys)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Benchmark storage list performance')
    parser.add_argument('-n', '--num_files', type=int, default=1000, help='Number of files to create')
    parser.add_argument('-r', '--rounds', type=int, default=100, help='Number of list() calls')

    args = parser.parse_args()

    tmpdir = tempfile.mkdtemp()
    file_s = ContentStorage_File(tmpdir, 'bench')
    sqlite_s = ContentStorage_Sqlite(tmpdir, 'bench')

    print(f'Populating {args.num_files} entries...')
    populate(file_s, sqlite_s, args.num_files)

    print(f'Running list() x {args.rounds}...\n')

    file_time, file_count = bench_list(file_s, args.rounds)
    sqlite_time, sqlite_count = bench_list(sqlite_s, args.rounds)

    print(f'{"Backend":<12} {"Keys":<8} {"Total (s)":<12} {"Per call (ms)":<14}')
    print('-' * 46)
    print(f'{"File":<12} {file_count:<8} {file_time:<12.4f} {file_time / args.rounds * 1000:<14.3f}')
    print(f'{"SQLite":<12} {sqlite_count:<8} {sqlite_time:<12.4f} {sqlite_time / args.rounds * 1000:<14.3f}')
    print(f'\nSQLite / File = {sqlite_time / file_time:.2f}x')

    sqlite_s.close()
