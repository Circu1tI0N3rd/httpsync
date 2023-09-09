#!/usr/bin/env python3

import sys
import os
import json
from time import sleep
from pathlib import Path
import multiprocessing as mp

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
        return {
            'file' : '%d' % p.stat().st_size,
            'url' : url
        }
    elif p.is_dir():
        curr = {}
        for path in p.iterdir():
            item = directoryIndex(path, url + '/' + path.name)
            if item is None:
                continue
            elif 'file' in item:
                if 'files' in curr:
                    curr['files'].append(item)
                else:
                    curr['files'] = [item,]
            else:
                curr[path.name] = item
        return curr
    else:
        return None

def indepthDictUpdate(A, B):
    if type(B) is dict and type(A) is dict:
        for key in B.keys():
            if key in A:
                if type(A[key]) is list and type(B[key]) is list:
                    A[key] += B[key]
                elif type(A[key]) is dict and type(B[key]) is dict:
                    indepthDictUpdate(A[key], B[key])
                elif type(A[key]) is dict:
                    A[key].update(B[key])
                else:
                    A[key] = B[key]
            else:
                A[key] = B[key]

def directoryIndex_ThreadSafe(pathQueue, outQueue, root_path, root_url):
    # Construct:
    # - Takes a job from pathQueue
    # - If the paper said DONE, done!
    # - Analyse that job
    # - If the job has informations needing clarity, pass it over to pathQueue
    # - Clarified items put inside outQueue
    # - Repeat
    while True:
        rel_path = pathQueue.get(block = True)
        if rel_path is None:
            sys.exit(0)
        elif type(rel_path) is list:
            # transverse the path
            p = Path(root_path)
            curr = {}
            ptr = curr
            url = root_url
            for subdir in rel_path:
                p /= subdir
                url += subdir + '/'
                ptr[subdir] = {}
                ptr = ptr[subdir]
            # check the path
            for sp in p.iterdir():
                if sp.is_dir():
                    pathQueue.put(rel_path + [sp.name,], block = True)
                elif sp.is_file():
                    if not 'files' in ptr:
                        ptr['files'] = []
                    ptr['files'].append({
                            'file' : '%d' % sp.stat().st_size,
                            'url' : url + sp.name
                        })
            # return the files
            if 'files' in ptr:
                outQueue.put(curr, block = True)

def directoryIndex_Threaded(parent, url, threads = 64, maxTries = 64):
    # check parent is directory
    p = Path(parent)
    if not p.is_dir():
        return None
    # construct queues
    pathQueue = mp.Queue()
    outQueue = mp.Queue()
    pathQueue.put([])
    # construct parent url
    if not url.endswith('/'):
        url += '/'
    # construct threads and start
    processes = []
    while len(processes) < threads:
        processes.append(mp.Process(
                target = directoryIndex_ThreadSafe,
                args = (pathQueue, outQueue, p, url)
            ))
        processes[len(processes) - 1].start()
    # build output
    index = {}
    trial = 1
    while True:
        try:
            subidx = outQueue.get(block = False)
            trial = 1
            indepthDictUpdate(index, subidx)
        except:
            if trial < maxTries:
                trial += 1
            else:
                # quit all processes
                for i in range(threads):
                    pathQueue.put(None)
                while len(processes) > 0:
                    proc = 0
                    while proc < len(processes):
                        if processes[proc].is_alive():
                            proc += 1
                        else:
                            processes.pop(proc)
                break
    # return
    return index
