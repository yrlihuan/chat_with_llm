import sys
import os.path

CUR_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.join(CUR_DIR, '../'))

import web.online_content as oc

if __name__ == '__main__':
    retrievers = oc.list_online_retrievers()
    print(retrievers)

    mrxwlb = oc.get_online_retriever('mrxwlb')
    parsed = mrxwlb.retrieve('20250301', force_fetch=False, force_parse=True, update_cache=True)

    print(parsed)