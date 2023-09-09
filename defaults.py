#!/usr/bin/env python3

from pathlib import Path

class Constants:
    def __setattr__(self, name, value):
        raise AttributeError('Read-only constant "%s"' % name)

class generalDefaults(Constants):
    source = None
    distro = 'debian'
    destination = Path.home() / 'httpsync'
    cache = Path.home() / 'httpsync_cache'
    whitelist = []
    blacklist = []

class aria2Defaults(Constants):
    detach = False
    listen_all = False
    port = 6800
    secret = ''

def_general = generalDefaults()
def_aria2 = aria2Defaults()
