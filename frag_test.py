from .frag import frag


def test_frag():
    pagememsize, memsize, frag_ratio = frag()
    assert frag_ratio < 1
    assert frag_ratio > .1
