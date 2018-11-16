from .frag import sysmem


def test_sysmem():
    pagememsize, memsize, frag_ratio = sysmem()
    assert frag_ratio < 1
