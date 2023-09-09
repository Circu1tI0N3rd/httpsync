#!/usr/bin/env python3

# python 3.9 and onward required

import aria2p

def searchURL(index, filename):
    for path in filesTree(index):
        for file in transverseDict(index, path):
            pos = file['url'].find(filename)
            if pos > 0 and pos < len(file['url']):
                return file['url']
    return None

def waitForAllFetches(aria2):
    fetches = aria2.get_downloads()
    while len(fetches) > 0:
        fails = []
        for fetch in fetches:
            try:
                fetch.update()
                if fetch.has_failed:
                    print('Will retry: %s' % fetch.name)
                    fails.append(fetch)
            except:
                pass
        if len(fails) > 0:
            aria2.retry_downloads(fails, clean=True)
        aria2.purge()
        fetches = aria2.get_downloads()

def fileListDownload(aria2, files, options):
    downloads = []
    for file in files:
        downloads.append(aria2.add_uris([file['url'],], options=options))
    return downloads

def indexDownload(aria2, index, parent):
    downloads = []
    if 'files' in index:
        options = aria2.get_global_options()
        options.dir = str(parent)
        downloads = downloads + fileListDownload(aria2, index['files'], options)
    for subdir in list(index.keys()):
        if subdir != 'files':
            downloads = downloads + indexDownload(aria2, index[subdir], parent / subdir)
    return downloads
