import sys
import os.path
import argparse

from web import online_content as oc

def run_help(parser):
    parser.print_help()

    print()
    print('Valid online retrievers:\n')
    retrievers = oc.list_online_retrievers()
    for name in retrievers:
        r = oc.get_online_retriever(name)
        print(f"{r.name}{': ' + r.description if r.description else ''}")

def run_list(args):
    retriever = oc.get_online_retriever(args.retriever)
    urls = retriever.list(**args.params)

    if len(urls) == 0:
        print('Retriever {args.retriever} doesn\'t support listing.')

    for r in urls:
        print(r)

def run_retrive(args):
    retriever = oc.get_online_retriever(args.retriever)
    parsed = retriever.retrieve(args.url_or_id, force_fetch=args.force_fetch, force_parse=args.force_parse, update_cache=args.update_cache)

    if args.print_results:
        print(parsed)

if __name__ == '__main__':
    dict_converter = lambda x: dict([tuple(kv.split('=')) for kv in x.split(',')])
    bool_converter = lambda x: x.lower() == 'true' or x == '1'

    parser = argparse.ArgumentParser(description='Test online retriever')
    parser.add_argument('--retriever', type=str, default='mrxwlb', help='Name of the online retriever')

    subparsers = parser.add_subparsers(dest='command')
    parser_help = subparsers.add_parser('help', help='Print help')

    parser_list = subparsers.add_parser('list', help='List urls')
    parser_list.add_argument('-n', type=int, default=50, help='Number of urls to list')
    parser_list.add_argument('--params', type=dict_converter, default={}, help='Parameters for the online retriever')

    parser_retrieve = subparsers.add_parser('retrieve', help='Retrieve content')
    parser_retrieve.add_argument('url_or_id')
    parser_retrieve.add_argument('--print_results', type=bool_converter, default=True)
    parser_retrieve.add_argument('--force-fetch', type=bool_converter, default=False)
    parser_retrieve.add_argument('--force-parse', type=bool_converter, default=False)
    parser_retrieve.add_argument('--update-cache', type=bool_converter, default=True)

    args = parser.parse_args()

    if args.command == 'help' or args.command is None:
        run_help(parser)
    elif args.command == 'list':
        run_list(args)
    elif args.command == 'retrieve':
        run_retrive(args)

    # retrievers = oc.list_online_retrievers()
    # print(retrievers)

    # mrxwlb = oc.get_online_retriever('mrxwlb')
    # parsed = mrxwlb.retrieve('20250301', force_fetch=False, force_parse=True, update_cache=True)

    # print(parsed)