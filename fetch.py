#!/usr/bin/env python3

# python 3.9 and onward required

import aria2p

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
