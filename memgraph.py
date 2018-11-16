import math
import time
from collections import defaultdict
import gc

import graphviz
from pympler import asizeof


def num_str(num):
    prefixes = {
        3: 'k',
        6: 'M',
        9: 'G',
        12: 'T',
        15: 'P',
        18: 'E',
        21: 'Z',
        24: 'Y'
    }
    precision = 3

    if num >= 10**precision:
        shifts = 0
        while num >= 10**precision:
            shifts += 1
            num /= 10
        truncated = round(num)

        prefix_power = math.ceil(shifts/3)*3
        prefix = prefixes[prefix_power]

        divisor = 10**(prefix_power-shifts)
        if divisor != 1:
            truncated /= divisor
        return str(truncated)+prefix
    else:
        return str(num)


class _MemInfo:
    def __init__(self):
        self.self_size = None  # memory used just by this class
        self.ref_size = None   # total memory referred to, including by children

    def calc_sizes(self):
        self.self_size = asizeof.asizeof(*self.objs, limit=0)
        self.ref_size = asizeof.asizeof(*self.objs)

    @property
    def type(self):
        # all self.objs are iterable, but not all can be indexed...
        for v in self.objs:
            return type(v)

    def __str__(self):
        return "{} objs: {}\nref: {}B, self: {}B".format(self.type.__name__, num_str(len(self.objs)), num_str(self.ref_size), num_str(self.self_size))

    def _graph(self, m, max, parent=None):  # parent is just used by edge
        raise NotImplementedError()


class _MemEdge(_MemInfo):
    def __init__(self):
        super().__init__()
        self._objs = {}

    def add(self, obj):
        self._objs[id(obj)] = obj

    @property
    def objs(self):
        return self._objs.values()


class _MemNode(_MemInfo):
    def __init__(self,  objs):
        super().__init__()
        self.objs = objs
        self.edges = defaultdict(_MemEdge)
        self.make_edges()
        self.calc_sizes()

    def get_children(self):
        return gc.get_referents(*self.objs)

    def make_edges(self):
        for obj in self.get_children():
            self.edges[type(obj)].add(obj)

        for edge in self.edges.values():
            edge.calc_sizes()


class _RootNode(_MemNode):
    # self_size = all objects passed in
    # ref_size includes overhead from the graph generation
    def __init__(self, objs):
        super().__init__(objs)

    def get_children(self):
        return self.objs

    @property
    def type(self):
        _RootNode.__name__ = "All"
        return _RootNode


class MemGraph:
    def __init__(self, objs):
        # try to identify all related objects?
        # for i in range(50):
        #     objs_tmp = gc.get_referents(*objs)
        #     if len(objs) == len(objs_tmp):
        #         break
        #     objs = objs_tmp

        self.root = _RootNode(objs)
        # RootNode classifies *all* objects by types into edges
        # sort by size, then limit?

        # all = gc.get_objects()
        # all_size = 0
        # for obj in all:
        #     all_size += sys.getsizeof(obj)

        # sorted_clusters = sorted(root.edges.values(), key=lambda x: x.ref_size, reverse=True)
        # important_types = set([edge.type for edge in sorted_clusters[:100]])
        # clustered_objs = [edge.objs for edge in sorted_clusters[:100]]
        clustered_objs = [edge.objs for edge in self.root.edges.values()]
        self.nodes = []

        for objs in clustered_objs:
            self.nodes.append(_MemNode(objs))

    def _render(self, name, directory, min_ref_percent):
        max_ref_size = self.root.self_size
        min_ref_size = max_ref_size * min_ref_percent

        name = 'memgraph'
        filename = time.strftime(name+"-%Y%m%d-%H%M%S.gv")
        self.g = graphviz.Digraph(name=name, directory="/tmp/", filename=filename)

        self._render_node(self.root, max_ref_size)

        for node in self.nodes:
            if node.ref_size > min_ref_size:
                self._render_node(node, max_ref_size)
                for edge in node.edges.values():
                    if edge.ref_size > min_ref_size:
                        self._render_edge(node, edge, max_ref_size)

    def _render_node(self, node, max_ref_size):
        w = max(5 * node.ref_size / max_ref_size, .2)
        self.g.node(name=str(id(node.type)), label=str(node), penwidth=str(w), weight=str(w))

    def _render_edge(self, node, edge, max_ref_size):
        w = max(5 * edge.ref_size / max_ref_size, .2)
        self.g.edge(tail_name=str(id(node.type)), head_name=str(id(edge.type)), label=str(edge), penwidth=str(w), weight=str(w))

    def render(self, name='memgraph', directory='/tmp', min_ref_percent=.05):
        self._render(name, directory, min_ref_percent)
        self.g.render()

    def view(self, name='memgraph', directory='/tmp', min_ref_percent=.05):
        self._render(name, directory, min_ref_percent)
        self.g.view()
