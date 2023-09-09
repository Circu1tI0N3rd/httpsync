#!/usr/bin/env python3

# python 3.9 and onward required

import sys
import re
import multiprocessing as mp
import datetime
import requests
from bs4 import BeautifulSoup

# parse Apache Directory Index table format
def parseApacheIndex(table):
    entries = []
    template = {
        'alt' : '',
        'href' : '',
        'timestamp' : '',
        'size' : '',
        'desc' : ''
    }
    # populate
    for row in table.find_all('tr'):
        entry = dict(template)
        elems = row.find_all('td')
        if len(elems) < 5:
            continue
        try:
            entry['alt'] = elems[0].img.get('alt')
        except:
            pass
        try:
            entry['href'] = elems[1].a.get('href')
        except:
            pass
        entry['timestamp'] = elems[2].contents[0].strip()
        entry['size'] = elems[3].contents[0].strip()
        entry['desc'] = elems[4].contents[0].strip()
        entries.append(entry)
    return entries

# parse NGINX AutoIndex pre
def parseNGINXIndex(pre):
    entries = []
    template = {
        'alt' : '',
        'href' : '',
        'timestamp' : '',
        'size' : ''
    }
    # create a copy of contents list
    items = list(pre.contents)
    # loop through list
    while len(items) > 0:
        entry = dict(template)
        try:
            # get url from a
            entry['href'] = items.pop(0).a.get('href')
            # get trailing content (timestamp and size)
            trail = items.pop(0).strip()
            for piece in trail.split():
                try:
                    t_date = datetime.datetime.strptime(piece, '%d-%b-%Y')
                    if t_date is not None:
                        entry['timestamp'] = t_date.strftime('%Y-%m-%d')
                except:
                    pass
                try:
                    t_time = datetime.datetime.strptime(piece, '%H:%M')
                    if t_time is not None:
                        entry['timestamp'] = entry['timestamp'] + t_time.strftime(' %H:%M')
                except:
                    pass
                entry['size'] = piece
            # guess alt using href same origin relative path
            if entry['href'].find('/') == 0:
                entry['alt'] = '[PARENTDIR]'
            elif entry['href'].endswith('/'):
                entry['alt'] = 'DIR'
            entries.append(entry)
        except:
            pass
    return entries

def formatIndexEntry(url, entry):
    item = {}
    if entry['alt'] == '[PARENTDIR]' or entry['href'].find('/') == 0:
        return None
    if entry['alt'] == '[DIR]':
        item['dir'] = entry['size']
    else:
        item['file'] = entry['size']
    item['timestamp'] = entry['timestamp']
    if url.endswith('/'):
        item['url'] = url + entry['href']
    else:
        item['url'] = url + '/' + entry['href']
    return item

def parseIndex(url):
    index = []
    r = requests.get(url)
    if r.headers['Content-Type'].find('text/html') == 0:
        soup = BeautifulSoup(r.text, 'html.parser')
        if r.headers['Server'].lower() == 'apache':
            for table in soup('table'):
                try:
                    for entry in parseApacheIndex(table):
                        item = formatIndexEntry(url, entry)
                        if type(item) is dict:
                            index.append(item)
                except:
                    pass
        elif r.headers['Server'].lower() == 'nginx':
            for pre in soup('pre'):
                try:
                    for entry in parseNGINXIndex(pre):
                        item = formatIndexEntry(url, entry)
                        if type(item) is dict:
                            index.append(item)
                except:
                    pass
    return index

def matchRegex(instr, regexes):
    for regex in regexes:
        if re.search(regex, instr) is not None:
            return True
    return False

def recurseIndexEntry(entry, whitelist = [], blacklist = []):
    index = []
    isWhitelist = len(whitelist) > 0
    isBlacklist = len(blacklist) > 0
    if isWhitelist and not matchRegex(entry['url'], whitelist):
        return index
    elif isBlacklist and matchRegex(entry['url'], blacklist):
        return index
    else:
        if 'file' in entry:
            index.append(entry)
            print(entry)
        elif 'dir' in entry:
            for item in parseIndex(entry['url']):
                index = index + recurseIndexEntry(entry, whitelist, blacklist)
        return index

def recurseIndex(url, whitelist = [], blacklist = []):
    return recurseIndexEntry({
                'dir' : '',
                'url' : url
            },
            whitelist,
            blacklist
        )

def evaluateIndexEntry_ThreadSafe(outQueue, entry, whitelist, blacklist):
    isWhitelist = len(whitelist) > 0
    isBlacklist = len(blacklist) > 0
    if isWhitelist and not matchRegex(entry['url'], whitelist):
        sys.exit(0)
    elif isBlacklist and matchRegex(entry['url'], blacklist):
        sys.exit(0)
    else:
        if 'file' in entry:
            outQueue.put(entry, block = True)
        elif 'dir' in entry:
            for item in parseIndex(entry['url']):
                outQueue.put(item, block = True)
        sys.exit(0)

def indexURL_Threaded(url, whitelist = [], blacklist = [], maxThreads = 8):
    processes = []
    indices = {}
    outQueue = mp.Queue()
    passes = 0

    # first process
    processes.append(mp.Process(
            target = evaluateIndexEntry_ThreadSafe,
            args = (outQueue, {'dir':'', 'url':url}, whitelist, blacklist)
        ))
    processes[0].start()

    # process manager
    while passes < 4:
        # handle trials
        if len(processes) > 0:
            passes = 0
        else:
            passes = passes + 1
        # generate process from queue entries
        while True:
            try:
                index = outQueue.get(block = False)
                if 'file' in index:
                    # filter
                    if len(whitelist) > 0 and not matchRegex(index['url'], whitelist):
                        continue
                    elif len(blacklist) > 0 and matchRegex(index['url'], blacklist):
                        continue
                    # skip processing for file
                    print(index)
                    # store in directory-oriented indices
                    path = index['url']
                    if url.endswith('/'):
                        path = path.removeprefix(url)
                    else:
                        path = path.removeprefix(url + '/')
                    path = path.split('/')
                    vect = indices
                    while len(path) > 1:
                        if not path[0] in vect:
                            vect[path[0]] = {}
                        vect = vect[path.pop(0)]
                    if not 'files' in vect:
                        vect['files'] = []
                    vect['files'].append(index)
                else:
                    processes.append(mp.Process(
                            target = evaluateIndexEntry_ThreadSafe,
                            args = (outQueue, index, whitelist, blacklist)
                        ))
            except:
                break
        # process
        thread = 0
        while thread < maxThreads:
            # handle processable threads less than available threads
            try:
                if processes[thread].is_alive():
                    thread = thread + 1
                else:
                    if processes[thread].exitcode is None:
                        processes[thread].start()
                        thread = thread + 1
                    else:
                        processes.pop(thread)
            except:
                break
    return indices
