#!/usr/bin/env python3

# python 3.9 and onward required

import sys
import os
import json
import platform
import subprocess
from time import sleep
from pathlib import Path
import aria2p
from pathtools import saveIndex, fileCleanup
from defaults import def_general, def_aria2
from argparser import ConsoleArguments
from loadconfig import generalOptions, aria2Options
from analyse import indexURL_Threaded
from difftree import diffIndices_Threaded, transverseDict, filesTree
from fetch import indexDownload, waitForAllFetches

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
    if inArgs.detach_aria2 != def_aria2.detach:
        aria2Opts.detach = inArgs.detach_aria2
    if inArgs.rpc_listen_all != def_aria2.listen_all:
        aria2Opts.listen_all = inArgs.rpc_listen_all
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
    # system check
    system = platform.system()
    if system == 'Windows' or system == 'Java':
        print('Unsupported OS, exiting...')
        sys.exit(1)
    # Treat Darwin as BSD
    elif system == 'FreeBSD' or system == 'OpenBSD' or system == 'Darwin':
        system = 'BSD'
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
    # aria2 instance start
    if not aOpts.detach:
        print('Creating aria2 instance')
        # allow using existing aria2 instance rather than spawning one (issue #1)
        aria2Args = ['aria2c', '--daemon', '--stop-with-process=%d' % os.getpid(), '--enable-rpc', '--rpc-listen-port=%s' % str(aOpts.port)]
        if aOpts.listen_all:
            aria2Args.append('--rpc-listen-all')
        if len(aOpts.secret) > 7:
            aria2Args.append('--rpc-secret="%s"' % aOpts.secret)
        aria2Proc = subprocess.run(aria2Args)
        sleep(1)
    print('Connecting to aria2 instance')
    aria2 = aria2p.API(aria2p.Client(
            host   = 'http://127.0.0.1',
            port   = aOpts.port,
            secret = aOpts.secret
        ))
    try:
        stat = aria2.get_stats()
    except:
        print('ERROR: aria2 RPC is not running or inaccessible.\n')
        sys.exit(1)
    # build index
    print('Building index from source')
    url = gOpts.source
    if not url.endswith('/'):
        url += '/'
    url += gOpts.distro
    newIndex = indexURL_Threaded(url, gOpts.whitelist, gOpts.blacklist, 16)
    # check existing index
    srcname = str(gOpts.source)
    if srcname.find('https') == 0:
        srcname = srcname.removeprefix('https://')
    else:
        srcname = srcname.removeprefix('http://')
    if srcname.endswith('/'):
        srcname = srcname.removesuffix('/')
    if srcname.find('/') >= 0:
        srcsplit = srcname.split('/')
        srcname = '_'.join(srcsplit)
    currIndexPath = gOpts.cache / str(srcname + '_' + gOpts.distro + '_index.json')
    currIndex = None
    newFiles = {}
    oldFiles = None
    addedFiles = None
    deletedFiles = None
    updatedFiles = None
    if currIndexPath.is_file():
        print('Current index is found')
        try:
            with currIndexPath.open('r') as f:
                currIndex = json.load(f)
        except Exception as e:
            print('Failed reading current index: %s' % str(e))
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
    print('Summary:')
    print(' - New files: %d' % listStat(newFiles))
    if oldFiles is not None:
        print(' - Old files: %d' % listStat(oldFiles))
    print(' - Files to be added: %d' % listStat(addedFiles))
    if deletedFiles is not None:
        print(' - Files to be deleted: %d' % listStat(deletedFiles))
    if updatedFiles is not None:
        print(' - Files to be updated: %d' % listStat(updatedFiles))
    # fetch new files
    # - fetch pool
    if 'pool' in newFiles:
        print('Downloading "pool"')
        print('Added %d files to downloads' % len(indexDownload(aria2, newFiles['pool'], gOpts.destination / gOpts.distro / 'pool')))
        waitForAllFetches(aria2)
        print('Downloaded "pool"')
    # - fetch dists
    if 'dists' in newFiles:
        print('Downloading "dists"')
        print('Added %d files to downloads' % len(indexDownload(aria2, newFiles['dists'], gOpts.destination / gOpts.distro / 'dists')))
        waitForAllFetches(aria2)
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
