import sys
import os.path
import argparse

from chat_with_llm.web import online_content as oc

def merge_retrieve_args(args):
    params = args.params.copy()
    params.update({'force_fetch': args.force_fetch, 'force_parse': args.force_parse, 'update_cache': args.update_cache})
    return params

def run_help(parser):
    parser.print_help()

    print()
    print('Valid online retrievers:\n')
    retrievers = oc.list_online_retrievers()
    for name in retrievers:
        r = oc.get_online_retriever(name)
        print(f"{r.name}{': ' + r.description if r.description else ''}")

def run_list(args):
    params = merge_retrieve_args(args)
    retriever = oc.get_online_retriever(args.retriever, **params)
    urls = retriever.list(args.n)

    if len(urls) == 0:
        print('Retriever {args.retriever} doesn\'t support listing.')

    for r in urls:
        print(r)

def run_retrive(args):
    params = merge_retrieve_args(args)
    retriever = oc.get_online_retriever(args.retriever, **params)
    parsed = retriever.retrieve(args.url_or_id)

    if args.print_results:
        print(parsed)

def run_retrieve_many(args):
    params = merge_retrieve_args(args)
    retriever = oc.get_online_retriever(args.retriever, **params)
    urls = retriever.list(args.n)

    rets = []
    for url in urls:
        print(f'Retrieving {url}...', end='')
        parsed = retriever.retrieve(url)
        if parsed:
            rets.append((url, parsed))
            print('done')
        else:
            print('failed')

if __name__ == '__main__':
    dict_converter = lambda x: dict([tuple(kv.split('=')) for kv in x.split(',')])
    bool_converter = lambda x: x.lower() == 'true' or x == '1'

    parser = argparse.ArgumentParser(description='Test online retriever')

    subparsers = parser.add_subparsers(dest='command')
    parser_help = subparsers.add_parser('help', help='Print help')

    parser_list = subparsers.add_parser('list', help='List urls')
    parser_list.add_argument('retriever', type=str, default='', help='Name of the online retriever')
    parser_list.add_argument('--params', type=dict_converter, default={}, help='Parameters for the online retriever')
    parser_list.add_argument('-n', type=int, default=20, help='Number of urls to list')

    parser_retrieve = subparsers.add_parser('retrieve', help='Retrieve content')
    parser_retrieve.add_argument('retriever', type=str, default='', help='Name of the online retriever')
    parser_retrieve.add_argument('url_or_id')
    parser_retrieve.add_argument('--params', type=dict_converter, default={}, help='Parameters for the online retriever')       
    parser_retrieve.add_argument('--print_results', type=bool_converter, default=True)
    parser_retrieve.add_argument('--force_fetch', type=bool_converter, default=False)
    parser_retrieve.add_argument('--force_parse', type=bool_converter, default=False)
    parser_retrieve.add_argument('--update_cache', type=bool_converter, default=True)

    parser_retrieve_many = subparsers.add_parser('retrieve_many', help='Retrieve content for many urls')
    parser_retrieve_many.add_argument('retriever', type=str, default='', help='Name of the online retriever')
    parser_retrieve_many.add_argument('--params', type=dict_converter, default={}, help='Parameters for the online retriever')       
    parser_retrieve_many.add_argument('-n', type=int, default=50, help='Number of urls to retrieve')
    parser_retrieve_many.add_argument('--force_fetch', type=bool_converter, default=False)
    parser_retrieve_many.add_argument('--force_parse', type=bool_converter, default=False)
    parser_retrieve_many.add_argument('--update_cache', type=bool_converter, default=True)

    args = parser.parse_args()

    if args.command == 'help' or args.command is None:
        run_help(parser)
        sys.exit(0)

    if args.retriever == '':
        print('Please specify the online retriever')
        run_help(parser)
        sys.exit(1)

    if args.retriever not in oc.list_online_retrievers():
        print(f'Unknown online retriever: {args.retriever}')
        run_help(parser)
        sys.exit(1)

    if args.command == 'list':
        run_list(args)
    elif args.command == 'retrieve':
        run_retrive(args)
    elif args.command == 'retrieve_many':
        run_retrieve_many(args)
    else:
        print('Unknown command')
        parser.print_help()
        sys.exit(1)
