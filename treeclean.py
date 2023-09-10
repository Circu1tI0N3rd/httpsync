#!/usr/bin/env python3
'''
Cleanup the destination to match the current index
'''

from pathlib import Path
from pathtools import directoryIndex, fileCleanup
from difftree import diffIndices_Threaded
from dicttools import listStat, filesTree

def pathIndex(dest, distro, src_url):
    # build file tree
    url = str(src_url)
    if not url.endswith('/'):
        url += '/'
    url += distro + '/'
    p = Path(dest) / distro
    return directoryIndex(p, url)

def treeCleanup(index, parent):
    if index is not None:
        delPaths = filesTree(index)
        delList = []
        for subdirs in delPaths:
            p = Path(parent)
            for subdir in subdirs:
                if subdir != 'files':
                    p /= subdir
            for file in transverseDict(deletedFiles, subdirs):
                url = str(file['url']).rsplit('/', maxsplit=1)
                delList.append(p / url[1])
        for delFile in delList:
            fileCleanup(delFile)

def pathTrim(dest, distro, src_url, index):
    print('Scanning destination (may take a while)')
    dIndex = pathIndex(dest, distro, src_url)
    print('Comapring to source structure')
    excess  = diffIndices_Threaded(index, dIndex, urlOnly = True)
    missing = diffIndices_Threaded(dIndex, index, urlOnly = True)
    print('Summary:')
    print(' - Excesses: %d' % listStat(excess))
    print(' - Not downloaded or failed: %d' % listStat(missing))
    print('Deleting')
    treeCleanup(excess, Path(dest) / distro)
    print('Done')
