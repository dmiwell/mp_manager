# -*- coding: utf-8 -*-


def build_batches(iterable, size):
    if not size:
        yield iterable
        return
    data = []
    for i in iterable:
        data.append(i)
        if len(data) % size == 0:
            yield data
            data = []
    if len(data):
        yield data
