#!/usr/bin/env python3
'''
Cleanup the destination to match the current index
'''

import json
from pathlib import Path
from pathtools import directoryIndex, fileCleanup, saveIndex
from difftree import diffIndices_Threaded
from dicttools import listStat, transverseDict, filesTree

def pathIndex(dest, distro, src_url):
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

def pathTrim(dest, distro, src_url, index, save_path = None, dry_run = False, use_cached = False):
    dIndex = None
    p = None
    if save_path is not None:
        srcname = str(src_url)
        if srcname.find('https') == 0:
            srcname = srcname.removeprefix('https://')
        else:
            srcname = srcname.removeprefix('http://')
        if srcname.endswith('/'):
            srcname = srcname.removesuffix('/')
        if srcname.find('/') >= 0:
            srcsplit = srcname.split('/')
            srcname = '_'.join(srcsplit)
        p = Path(save_path) / str(srcname + '_' + distro + '_dir.json')
    if use_cached and not p.is_file():
        use_cached = False
        if p.is_dir():
            save_path = None
            p = None
    if use_cached:
        print('Using previously scanned directory structure')
        try:
            with p.open('r') as f:
                dIndex = json.load(f)
        except:
            print('Cannot read, trying rescan')
            use_cached = False
    if not use_cached:
        print('Scanning destination (may take a while): %s' % str(Path(dest) / distro))
        dIndex = pathIndex(dest, distro, src_url)
    print('Comapring to source structure')
    excess  = diffIndices_Threaded(index, dIndex, urlOnly = True)
    missing = diffIndices_Threaded(dIndex, index, urlOnly = True)
    print('Summary:')
    print(' - Excesses: %d' % listStat(excess))
    print(' - Not downloaded or failed: %d' % listStat(missing))
    if save_path is not None and not use_cached:
        if p.is_dir():
            print('Cannot save to path (which is a folder): %s' % str(p))
        else:
            saveIndex(dIndex, p)
            print('Directory structure saved to "%s"' % str(p))
    if not dry_run:
        print('Deleting')
        treeCleanup(excess, Path(dest) / distro)
        print('Done')
