### Memtools

This has a couple of utilities/examples of finding memory leaks in python.

Most important is MemGraph, which uses graphviz to show which classes refer
to the most memory.

#### Memgraph

MemGraph requires `graphviz` and `pympler`.

Copy memgraph.py to your project, then:

```python
    from pympler import muppy
    from memgraph import MemGraph

    g = MemGraph(muppy.get_objects())
    g.view()  # or render()
```

`view` and `render` both share the same signature: `(name='memgraph', directory='.', min_ref_percent=.05)`.

Files are rendered to `directory/name-%Y%m%d-%H%M%S.gv` (`.pdf`).

By default, only usage that accounts for >5% of memory usage is represented. This applies to nodes and edges.

***This is an expensive operation, both in CPU and memory.***

#### Output

Here's a simple, unbalanced case:

![Imgur](https://i.imgur.com/OlwHum5.png)

Each node and edge show the number of instances (objs), the total referred to memory
(including self), and memory just used by class instances (self).

All objs is a special case and isn't linked. For it, objs and self represent all objects
passed in to MemGraph. ref includes memory used in generating the graph. ref is
not used anywhere - `min_ref_percent` is only based on objects passed in to MemGraph.

-----------------------------

Here is more complex output from test_classify:

![Sample output from test_classify](https://i.imgur.com/xoz73fI.png)


This output is actually identical to the first example, but with ReferencesMem using less memory.



