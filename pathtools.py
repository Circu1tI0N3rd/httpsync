#!/usr/bin/env python3

import sys
import os
import json
from time import sleep
from pathlib import Path
import multiprocessing as mp
from dicttools import indepthDictUpdate

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

def directoryIndex(parent, url):
    p = Path(parent)
    if p.is_file():
        return { 'file' : '%d' % p.stat().st_size, 'url' : url }
    elif p.is_dir():
        tree = {}
        for path, subdirs, files in os.walk(str(p)):
            c_url = str(url)
            if not c_url.endswith('/'):
                c_url += '/'
            ptr = tree
            for subdir in path.removeprefix(str(p) + '/').split('/'):
                c_url += subdir + '/'
                if not subdir in ptr:
                    ptr[subdir] = {}
                ptr = ptr[subdir]
            ptr['files'] = [{
                'file' : '%d' % Path(path + '/' + file).stat().st_size,
                'url' : c_url + file
            } for file in files]
        return tree
    else:
        return {}
