from pympler import asizeof, muppy
from .memgraph import _MemInfo, _MemNode, _RootNode, _MemEdge, MemGraph, num_str


def test_num_str():
    assert num_str(1) == "1"
    assert num_str(12) == "12"
    assert num_str(123) == "123"
    assert num_str(1234) == "1.23k"
    assert num_str(12345) == "12.3k"
    assert num_str(123456) == "123k"
    assert num_str(1234567) == "1.23M"

    assert num_str(1000000) == "1M"


class TestMemInfo:
    def test_leaf(self):
        info = _MemInfo()
        info.objs = ["leaf obj"]
        info.calc_sizes()

        assert info.ref_size == info.self_size

    def test_child(self):
        child = "child"
        parent = [child]
        info = _MemInfo()
        info.objs = [parent]
        info.calc_sizes()

        assert info.ref_size == info.self_size + asizeof.asizeof(child)

    def test_str(self):
        info = _MemInfo()
        info.objs = ["1", "2"]
        info.calc_sizes()

        assert str(info) == "str objs: 2\nref: 112B, self: 112B"


class TestMemEdge:
    def test_dedup(self):
        obj = "leaf obj"
        edge = _MemEdge()
        edge.add(obj)
        edge.add(obj)
        edge.calc_sizes()

        assert edge.type is str
        assert len(edge.objs) == 1


class TestMemNode:
    child1 = "child1"
    child2 = "child2"
    child3 = 3
    parent = [child1, child2, child3]
    grandparent = [parent, child1]

    def test_type(self):
        t = _MemNode([1])
        assert t.type is int

    def test_basic(self):
        basic = _MemNode([self.parent])

        assert len(basic.edges) == 2
        assert basic.edges[str].self_size == asizeof.asizeof(self.child1) * 2

    def test_repeat(self):
        repeat = _MemNode([self.grandparent, self.parent])
        basic = _MemNode([self.grandparent])

        assert repeat.ref_size == basic.ref_size
        assert repeat.ref_size > 0

        assert len(repeat.edges[str].objs) == 2

    def test_str(self):
        node = _MemNode([self.parent])
        assert str(node) == "list objs: 1\nref: 232B, self: 88B"


class TestRootNode:
    def test_mix(self):
        child1 = "child1"
        child2 = "child2"
        child3 = 3
        parent1 = [child1, child2]
        parent2 = [child2, child3]

        root = _RootNode([child1, child2, child3, parent1, parent2])

        assert root.ref_size == root.self_size
        assert str(root) == "All objs: 5\nref: 304B, self: 304B"

        root2 = _RootNode([parent1, parent2])
        assert root2.ref_size > root2.self_size
        assert root.ref_size == root2.ref_size

    def test_find_children(self):
        child1 = "child1"
        child2 = 2
        parent = [child1, child2]
        node = _RootNode([parent, child1, child2])

        assert len(node.edges) == 3


class TestMemGraph:
    def test_basic(self):
        child1 = "child1"
        child2 = "child2"
        parent1 = [child1]
        parent2 = [child1, child2]

        g = MemGraph([parent1, parent2, child1, child2])
        assert len(g.nodes) == 2  # 2 types, str, list

        for node in g.nodes:
            assert len(node.objs) == 2
            if node.type is list:
                assert len(node.edges) == 1
                edge = node.edges[str]
                assert len(edge.objs) == 2
            else:
                assert node.type is str
                assert len(node.edges) == 0

        g.render()

    def test_custom_class(self):
        class Custom:
            def __init__(self, *args):
                for i in range(len(args)):
                    setattr(self, "arg"+str(i), args[i])

        child1 = "child1"
        child2 = 2
        custom = Custom(child1, child2)

        g = MemGraph([child1, child2, custom])
        assert len(g.nodes) == 3

        g.render()

    def test_classify(self):
        class ReferencesMem:
            def __init__(self):
                self.stuff = []
                for i in range(250000):
                    self.stuff.append(i)

        r = ReferencesMem()

        g = MemGraph(muppy.get_objects())
        g.view()

