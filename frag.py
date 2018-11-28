import os
import gc
from collections import defaultdict
import sys

from .memgraph import num_str


def frag():
    objs = gc.get_objects()
    pages = defaultdict(list)
    page_size = os.sysconf('SC_PAGE_SIZE')

    memsize = 0
    for obj in objs:
        objmem = sys.getsizeof(obj)
        start = id(obj)
        end = (id(obj)+objmem-1)
        for page in range(int(start/page_size), int(end/page_size)+1):
            pages[page].append(obj)
        memsize += objmem

    sysmem = len(pages)*page_size

    return num_str(sysmem) + "B", num_str(memsize) + "B", float(memsize) / sysmem
