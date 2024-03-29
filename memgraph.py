# Copyright (c) 2018 David Hilton <dhiltonp@gmail.com>
#
# This work is licensed under the terms of the MIT license.
# see https://github.com/dhiltonp/memtools

import math
import time
from collections import defaultdict
import gc

import graphviz
from pympler import asizeof


def num_str(num, precision=3):
    num = float(num)
    for unit in ['', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']:
        if num < 10**3:
            break
        num /= 10**3

    # how many digits should we show?
    tmp_num = num
    for i in range(precision):
        if tmp_num < 1:
            break
        tmp_num /= 10
        precision -= 1
    if num.is_integer():
        precision = 0

    format_str = "%."+str(precision)+"f"+unit
    return format_str % (num)


def find_referrers(obj, all_objects=None):
    """
    Returns all objects that directly or indirectly refer to obj, restricted to those in all_objects.

    If all_objects isn't passed, it will be set via gc.get_objects().

    If you want to include stack frames (to be able to find the function where objects are defined
    or referrenced), use all_objects=muppy.get_objects(include_frames=True)
    """
    if all_objects is None:
        gc.collect()
        all_objects = gc.get_objects()
    referred_objects = [obj]
    referred_object_ids = {id(obj)}
    all_object_ids = {id(o) for o in all_objects}
    referred_objects_length = len(referred_objects)
    while True:
        referrers = gc.get_referrers(*referred_objects)
        for referrer in referrers:
            if id(referrer) not in referred_object_ids and id(referrer) in all_object_ids:
                referred_objects.append(referrer)
                referred_object_ids.add(id(referrer))
        if referred_objects_length != len(referred_objects):
            referred_objects_length = len(referred_objects)
        else:
            return referred_objects


class _MemInfo(object):
    def __init__(self):
        self.has_dicts = False
        self.self_size = None  # memory used just by this class
        self.ref_size = None   # total memory referred to, including by children

    def calc_sizes(self):
        self.self_size = asizeof.asizeof(*self.objs, limit=0)
        self.ref_size = asizeof.asizeof(*self.objs)

    @property
    def type(self):
        # all self.objs are iterable, but not all can be indexed...
        for v in self.objs:
            if self.has_dicts and type(v) == dict:
                continue
            if type(v).__name__ == "instance":
                return v.__class__
            return type(v)

    @property
    def uname(self):
        """
        returns a unique name based on the class
        :return:
        """
        t = self.type
        return t.__module__ + "." + t.__name__ + " (" + str(id(t)) + ")"

    def __str__(self):
        if self.has_dicts:
            obj_count = len(self.objs) / 2
        else:
            obj_count = len(self.objs)
        return "{} objs: {}\nref: {}B, self: {}B".format(self.type.__name__, num_str(obj_count),
                                                         num_str(self.ref_size), num_str(self.self_size))

    def _graph(self, m, max, parent=None):  # parent is just used by edge
        raise NotImplementedError()


class _MemEdge(_MemInfo):
    def __init__(self):
        super(_MemEdge, self).__init__()
        self._objs = {}

    def add(self, obj):
        self._objs[id(obj)] = obj

    @property
    def objs(self):
        return self._objs.values()


class _MemNode(_MemInfo):
    def __init__(self,  objs):
        super(_MemNode, self).__init__()
        self.objs = objs
        self.edges = defaultdict(_MemEdge)
        self.make_edges()
        self.calc_sizes()

    def get_children(self):
        # we add __dict__ dicts into self.objs to better track memory usage.
        refs = gc.get_referents(*self.objs)

        # find __dict__s
        dicts = []
        for obj in self.objs:  # iterating to determine if type has __dict__
            if not hasattr(obj, "__dict__"):
                break
            self.has_dicts = True
            for obj in self.objs:
                dicts.append(getattr(obj, "__dict__"))
            break
        dicts = {id(x): x for x in dicts}

        # remove dicts from refs
        refs = {id(x): x for x in refs if id(x) not in dicts}
        # find referents from __dict__s and add those to other referents
        dicts_refs = {id(x): x for x in gc.get_referents(*dicts.values())}
        refs.update(dicts_refs)

        # add __dicts__ to objs
        tmp_objs = {id(x): x for x in self.objs}
        tmp_objs.update(dicts)
        self.objs = tmp_objs.values()

        return refs.values()

    def make_edges(self):
        for obj in self.get_children():
            self.edges[type(obj)].add(obj)

        for edge in self.edges.values():
            edge.calc_sizes()


class _RootNode(_MemNode):
    # self_size = all objects passed in
    # ref_size includes overhead from the graph generation
    def __init__(self, objs):
        super(_RootNode, self).__init__(objs)

    def get_children(self):
        return self.objs

    @property
    def type(self):
        _RootNode.__name__ = "All"
        return _RootNode


class MemGraph:
    def __init__(self, objs):
        # We feed all objects into a "Root" node.
        #  This classifies edges by class, which we
        #  then use as input into actual Nodes.
        self.root = _RootNode(objs)
        self.g = None
        self.nodes = []

        clustered_objs = [edge.objs for edge in self.root.edges.values()]
        for objs in clustered_objs:
            self.nodes.append(_MemNode(objs))

    def _render(self, min_ref_percent):
        max_ref_size = self.root.self_size+.000000001
        min_ref_size = float(max_ref_size * min_ref_percent)

        self._render_node(self.root, max_ref_size)

        for node in self.nodes:
            if node.ref_size > min_ref_size:
                self._render_node(node, max_ref_size)
                for edge in node.edges.values():
                    if edge.ref_size > min_ref_size:
                        self._render_edge(node, edge, max_ref_size)

    def _render_node(self, node, max_ref_size):
        w = max(5 * node.ref_size / max_ref_size, .2)
        self.g.node(name=node.uname, label=str(node), penwidth=str(w), weight=str(w), url=node.uname)

    def _render_edge(self, node, edge, max_ref_size):
        w = max(5 * edge.ref_size / max_ref_size, .2)
        self.g.edge(tail_name=node.uname, head_name=edge.uname, label=str(edge), penwidth=str(w), weight=str(w))

    def render(self, min_ref_percent=.05, name="memgraph",
               directory=None, view=False, cleanup=False,
               format=None, renderer=None, formatter=None):
        """
        :param min_ref_percent: minimum memory usage to be rendered
        :param name: name of graph, also prefix for output file
        :param directory: directory for source saving and rendering.
        :param view: Open the rendered result with the default application
        :param cleanup: Delete the source file after rendering.
        :param format: The output format used for rendering (``'pdf'``, ``'png'``, ``'svg'``, etc.)
        :param renderer: The output renderer used for rendering (``'cairo'``, ``'gd'``, ...).
        :param formatter: The output formatter used for rendering (``'cairo'``, ``'gd'``, ...).
        """
        self.g = graphviz.Digraph(name=name)
        self._render(min_ref_percent)
        
        filename = time.strftime(name+"-%Y%m%d-%H%M%S.gv")
        self.g.render(filename=filename, directory=directory, view=view, cleanup=cleanup,
                      format=format, renderer=renderer, formatter=formatter)

    def view(self, min_ref_percent=.05, name="memgraph", directory=None, cleanup=False):
        self.render(min_ref_percent=min_ref_percent, name=name,
                    directory=directory, cleanup=cleanup, view=True)
