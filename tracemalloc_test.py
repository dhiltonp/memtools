import linecache
import os


def test_tracemalloc():
    import tracemalloc

    tracemalloc.start()

    # # show top memory locations...
    def diff(new, old):
        diff = new.compare_to(old, 'lineno')
        print("top 10 since last tracemalloc")
        for stat in diff[:10]:
            print(stat)

    def print_stats(stats):
        print("Top 20 lines")
        for index, stat in enumerate(stats[:20], 1):
            frame = stat.traceback[0]
            # replace "/path/to/module/file.py" with "module/file.py"
            filename = os.sep.join(frame.filename.split(os.sep)[-2:])
            print("#%s: %s:%s: %.1f KiB"
                     % (index, filename, frame.lineno, stat.size / 1024))
            line = linecache.getline(frame.filename, frame.lineno).strip()
            if line:
                print('    %s' % line)

    # results = []
    # for i in range(14):
    #     snapshot = tracemalloc.take_snapshot()
    #     # top_stats = snapshot1.statistics('lineno')
    #     if i %3 == 0:
    #         results.append((snapshot, list(range(1000))))
    #     else:
    #         results.append((snapshot, ))
    #
    # for i in range(len(results)-2):
    #     diff(results[i+1][0], results[i][0])

    import gc
    # gc.disable()

    print("HOHOHOHOHOHOHOH")
    snapshots = []
    statistics = []
    tmp=0
    for i in range(14):
        snapshot = tracemalloc.take_snapshot()
        statistics.append(snapshot.statistics('lineno'))
        snapshots.append((snapshot, ))
        if i % 3 == 0:
            tmp = list(range(1000))
        else:
            tmp = None

    # for i in range(len(results)-2):
    #     diff(results[i+1][0], results[i][0])

    for stats in statistics:
        print_stats(stats)
