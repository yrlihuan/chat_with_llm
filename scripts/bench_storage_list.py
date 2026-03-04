import argparse
import tempfile
import time
import os.path

from chat_with_llm import storage


def bench_list(storage, rounds):
    t0 = time.time()
    for _ in range(rounds):
        keys = storage.list()
        for k in keys:
            storage.load_bytes(k)
    t1 = time.time()
    return t1 - t0, len(keys)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Benchmark storage list performance')

    parser.add_argument('--rounds', type=int, default=1)
    parser.add_argument('--type', default='chat_history')
    parser.add_argument('--identifier', default='sum_hn')
    parser.add_argument('--class1', default='file')
    parser.add_argument('--class2', default='sqlite')

    args = parser.parse_args()

    tmpdir = tempfile.mkdtemp()
    s1 = storage.get_storage(args.type, args.identifier, storage_class=args.class1)
    s2 = storage.get_storage(args.type, args.identifier, storage_class=args.class2)

    s1_time, s1_count = bench_list(s1, args.rounds)
    s2_time, s2_count = bench_list(s2, args.rounds)

    print(f'{"Backend":<12} {"Keys":<8} {"Total (s)":<12} {"Per call (ms)":<14}')
    print('-' * 46)
    print(f'{args.class1:<12} {s1_count:<8} {s1_time:<12.4f} {s1_time / args.rounds * 1000:<14.3f}')
    print(f'{args.class2:<12} {s2_count:<8} {s2_time:<12.4f} {s2_time / args.rounds * 1000:<14.3f}')
    print(f'\n{args.class2} / {args.class1} = {s2_time / s1_time:.2f}x')

    s1.close()
    s2.close()
