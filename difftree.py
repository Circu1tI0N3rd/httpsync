#!/usr/bin/env python3

# python 3.9 and onward required

import sys
import json
from pathlib import Path
import subprocess
import multiprocessing as mp
from pathtools import changedir, fileCleanup

def prepareDiffStructure(filesList, urlOnly = False):
    filesStrList = []
    for file in filesList:
        strip = None
        if urlOnly:
            strip = { 'url' : file['url'] }
        else:
            strip = file
        filesStrList.append(json.dumps(strip, sort_keys=True))
    filesStrList.sort()
    return filesStrList

def revertDiffStructure(filesStrList, urlOnly = False):
    filesList = []
    for file in filesStrList:
        reverted = json.loads(file)
        if urlOnly:
            reverted['file'] = '-'
        filesList.append(reverted)
    return filesList

def generateFileToDiff(filesList, path):
    strlist = prepareDiffStructure(filesList)
    written = 0
    # check folder existence
    p = changedir(path, '..')
    if not p.exists():
        p.mkdir(parents=True)
    with open(path, 'w') as f:
        written += f.write(strlist.pop(0))
        while len(strlist) > 0:
            written += f.write('\n')
            written += f.write(strlist.pop(0))
    return written

def diffFileUNIXCmd(file_a, file_b):
    # test for comm tools
    try:
        subprocess.check_output(['which', 'comm'])
    except:
        raise ModuleNotFoundError('"coreutils" isn\'t installed.')
    outlist = []
    try:
        diff = subprocess.check_output(['/usr/bin/comm', '-13', file_a, file_b]).decode()
        diffFiles = diff.split('\n')
        for file in diffFiles:
            file.strip()
            if len(file) > 0:
                outlist.append(json.loads(file))
    except:
        pass
    return outlist

def diffIndices(indexA, indexB, method = '', working_dir = '/tmp', depth = ''):
    diffIndex = {}
    for key in indexB.keys():
        if key in indexA:
            if key == 'files':
                if method.lower() == 'unix':
                    diffIndex['files'] = []
                    file_a = working_dir + ('' if working_dir.endswith('/') else '/') + str(depth)
                    file_b = str(file_a)
                    file_a += '.a.json'
                    file_b += '.b.json'
                    generateFileToDiff(indexA[key], file_a)
                    generateFileToDiff(indexB[key], file_b)
                    diffIndex['files'] = diffFileUNIXCmd(file_a, file_b)
                    fileCleanup(file_a)
                    fileCleanup(file_b)
                else:
                    filesA = prepareDiffStructure(indexA[key])
                    filesB = prepareDiffStructure(indexB[key])
                    diffIndex['files'] = revertDiffStructure(set(filesB) - set(filesA))
            else:
                if type(indexA[key]) is dict:
                    diffIndex[key] = {}
                elif type(indexA[key]) is list:
                    diffIndex[key] = []
                else:
                    diffIndex[key] = None
                diffIndex[key] = diffIndices(indexA[key], indexB[key], working_dir, depth + '-' + key)
        else:
            # This tree is new: cloning tree
            if type(indexB[key]) is dict:
                diffIndex[key] = dict(indexB[key])
            elif type(indexB[key]) is list:
                diffIndex[key] = list(indexB[key])
            else:
                diffIndex[key] = indexB[key]
    return diffIndex

def transverseDict(tree, keys):
    dest = tree
    for key in keys:
        if key in dest:
            dest = dest[key]
        else:
            return None
    return dest

def filesTree(tree, path = []):
    lst = []
    for key in tree.keys():
        if key == 'files':
            lst.append(tuple(path + [key]))
        else:
            lst += filesTree(tree[key], path + [key])
    return lst

def diffIndexBuiltin_ThreadSafe(diffOut, indexA, indexB, path, urlOnly = False):
    listA = transverseDict(indexA, path)
    listB = transverseDict(indexB, path)
    if type(listA) is list and type(listB) is list:
        filesA = prepareDiffStructure(listA, urlOnly)
        filesB = prepareDiffStructure(listB, urlOnly)
        diffFiles = revertDiffStructure(set(filesB) - set(filesA), urlOnly)
        if len(diffFiles) > 0:
            diffTree = {}
            subtree = diffTree
            for key in keys:
                if key == 'files':
                    subtree[key] = diffFiles
                else:
                    subtree[key] = {}
                    subtree = subtree[key]
            diffOut.put(diffTree, block = True)
    sys.exit(0)

def diffIndices_Threaded(indexA, indexB, urlOnly = False, maxThreads = 64):
    diffIndex = {}
    diffOut = mp.Queue()
    processes = []
    # create processes
    for path in filesTree(indexB):
        processes.append(mp.Process(
                target = diffIndexBuiltin_ThreadSafe,
                args = (diffOut, indexA, indexB, path, urlOnly)
            ))
    # iterate threads
    while len(processes) > 0:
        # Grab output
        while True:
            try:
                partial = diffOut.get(block = False)
                if partial is not None:
                    diffIndex = {**diffIndex, **partial}
            except:
                break;
        # Initiates new threads
        threads = 0
        while threads < maxThreads and threads < len(processes):
            if processes[threads].is_alive():
                threads += 1
            else:
                if processes[threads].exitcode is None:
                    processes[threads].start()
                    threads += 1
                else:
                    processes.pop(threads)
    # return
    return diffIndex
