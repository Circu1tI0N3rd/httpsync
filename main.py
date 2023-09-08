#!/usr/bin/env python3

# python 3.9 and onward required

import sys
import os
import json
from pathlib import Path
import aria2p
from pathtools import saveIndex, fileCleanup
from defaults import def_general, def_aria2
from argparser import ConsoleArguments
from loadconfig import generalOptions, aria2Options
from analyse import indexURL_Threaded
from difftree import diffIndices_Threaded, transverseDict, filesTree
from fetch import indexDownload

def updateOptions(generalOpts, aria2Opts, inArgs):
    if inArgs.source != def_general.source:
        generalOpts.source = inArgs.source
    if inArgs.distro != def_general.distro:
        generalOpts.distro = inArgs.distro
    if inArgs.destination != def_general.destination:
        generalOpts.destination = inArgs.destination
    if inArgs.cache != def_general.cache:
        generalOpts.cache = inArgs.cache
    if inArgs.include != def_general.whitelist:
        generalOpts.whitelist = inArgs.include
    if inArgs.exclude != def_general.blacklist:
        generalOpts.blacklist = inArgs.exclude
    if inArgs.rpc_host != def_aria2.host:
        aria2Opts.host = inArgs.rpc_host
    if inArgs.rpc_port != def_aria2.port:
        aria2Opts.port = inArgs.rpc_port
    if inArgs.rpc_secret != def_aria2.secret:
        aria2Opts.secret = inArgs.rpc_secret

def tryCreateDirs(path):
    p = Path(path)
    try:
        p.mkdir(parents=True)
    except:
        print('ERROR: Cannot create dir(s) %s.\n' % str(p))
        sys.exit(1)

def permissionCheck(path):
    p = Path(path) / 'lck'
    try:
        p.touch(0o644)
        os.remove(str(p))
    except FileExistsError:
        try:
            os.remove(str(p))
            permissionCheck(path)
        except:
            print('ERROR: Folder access failed.\n')
            sys.exit(1)
    except:
        print('ERROR: Folder access failed.\n')
        sys.exit(1)

def listStat(index):
    count = 0
    filesPath = filesTree(index)
    for path in filesPath:
        count += len(transverseDict(index, path))
    return count

def main():
    # get args
    Args = ConsoleArguments()
    Args.parse()
    # build config
    gOpts = None
    if Args.config is None:
        gOpts = generalOptions()
    else:
        gOpts = generalOptions(Args.config)
    aOpts = aria2Options(gOpts)
    if not Args.default_values:
        updateOptions(gOpts, aOpts, Args)
    if Args.save and Args.config is not None:
        gOpts.flush(True)
        aOpts.flush(True)
    # requirement check: source specified
    if gOpts.source is None or gOpts.source == '':
        Args.parser.print_help()
        print("\nERROR: Repository source unspecified.\n")
        sys.exit(1)
    # permission check & build paths
    if gOpts.destination.is_dir():
        permissionCheck(gOpts.destination)
    else:
        tryCreateDirs(gOpts.destination)
    if gOpts.cache.is_dir():
        permissionCheck(gOpts.cache)
    else:
        tryCreateDirs(gOpts.cache)
    # aria2 initialise
    host = aOpts.host
    if host.endswith('/'):
        host.removesuffix('/')
    aria2 = aria2p.API(aria2p.Client(
            host   = host,
            port   = aOpts.port,
            secret = aOpts.secret
        ))
    try:
        stat = aria2.get_stats()
    except:
        print('ERROR: aria2 RPC is not running or inaccessible.\n')
        sys.exit(1)
    # build index
    newIndex = indexURL_Threaded(gOpts.source, gOpts.whitelist, gOpts.blacklist, 16)
    # check existing index
    currIndexPath = gOpts.cache / str(gOpts.source + '_' + gOpts.distro + '_index.json')
    currIndex = None
    newFiles = {}
    oldFiles = None
    addedFiles = None
    deletedFiles = None
    updatedFiles = None
    if currIndexPath.is_file():
        try:
            with currIndexPath.open('r') as f:
                currIndex = json.read(f)
        except:
            pass
    # - build diff index (add & remove)
    if currIndex is None:
        newFiles = newIndex
        addedFiles = newIndex
    else:
        newFiles = diffIndices_Threaded(currIndex, newIndex, maxThreads = 64)
        oldFiles = diffIndices_Threaded(newIndex, currIndex, maxThreads = 64)
        # - categorise files update/add/delete
        addedFiles   = diffIndices_Threaded(oldFiles, newFiles, True, 64)
        deletedFiles = diffIndices_Threaded(newFiles, oldFiles, True, 64)
        updatedFiles = diffIndices_Threaded(addedFiles, newFiles, True, 64)
    # save new index
    saveIndex(newIndex, currIndexPath)
    # statistics
    print('New files: %d' % listStat(newFiles))
    if oldFiles is not None:
        print('Old files: %d' % listStat(oldFiles))
    print('Files to be added: %d' % listStat(addedFiles))
    if deletedFiles is not None:
        print('Files to be deleted: %d' % listStat(deletedFiles))
    if updatedFiles is not None:
        print('Files to be updated: %d' % listStat(updatedFiles))
    # fetch new files
    # - fetch pool
    if 'pool' in newFiles:
        print('Downloading "pool"')
        poolFetches = indexDownload(aria2, newFiles['pool'], gOpts.destination / gOpts.distro)
        while len(poolFetches) > 0:
            pos = 0
            while pos < len(poolFetches):
                poolFetches[pos].update()
                if poolFetches[pos].is_complete:
                    poolFetches[pos].remove(False, False)
                    poolFetches.pop(pos)
                else:
                    pos += 1
        print('Downloaded "pool"')
    # - fetch dists
    if 'dists' in newFiles:
        print('Downloading "dists"')
        distsFetches = indexDownload(aria2, newFiles['dists'], gOpts.destination / gOpts.distro)
        while len(distsFetches) > 0:
            pos = 0
            while pos < len(distsFetches):
                distsFetches[pos].update()
                if distsFetches[pos].is_complete:
                    distsFetches[pos].remove(False, False)
                    distsFetches.pop(pos)
                else:
                    pos += 1
        print('Downloaded "dists"')
    # remove old files
    if deletedFiles is not None:
        delPaths = filesTree(deletedFiles)
        delList = []
        for subdirs in delPaths:
            path = Path(gOpts.destination) / gOpts.distro
            for subdir in subdirs:
                if subdir != 'files':
                    path /= subdir
            for file in transverseDict(deletedFiles, subdirs):
                url = str(file['url']).rsplit('/', maxsplit=1)
                delList.append(path / url[1])
        for delFile in delList:
            fileCleanup(delFile)
    # return
    print('Mirror complete!\n')
    sys.exit(0)

if __name__ == '__main__':
    main()
