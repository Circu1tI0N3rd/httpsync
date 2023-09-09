#!/usr/bin/env python3

import os
import json
from pathlib import Path

def changedir(curr, ext):
    c = Path(curr)
    e = Path(ext)
    if e == Path('..'):
        if c == Path('..') or c.name == '..':
            return c / e
        if c == Path('.') or c.parent == Path('.'):
            return e
        if c == Path('/'):
            return c
        return c.parent
    if str(e).find('/') == 0:
        return e
    return c / e

def saveIndex(index, path):
    p = Path(path)
    with p.open('w', encoding='utf-8') as f:
        json.dump(index, f, indent=4, sort_keys=True)

def updateIndex(index, path):
    with open(path, 'r') as f:
        index |= json.load(f)

def fileCleanup(path):
    p = Path(path)
    empty = True
    if p.exists():
        while empty:
            try:
                if p.is_file():
                    os.remove(str(p))
                elif p.is_dir():
                    for subpath in p.iterdir():
                        empty = False
                        break
                    if empty:
                        p.rmdir()
                else:
                    empty = False
                # move 1 level upward
                p = changedir(p, '..')
            except:
                break
