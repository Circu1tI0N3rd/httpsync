#!/usr/bin/env python3

# python 3.9 and onward required

from defaults import def_general, def_aria2
import argparse
from pathlib import Path
import subprocess
import sys
import json
import os

class Argument:
    value = None
    def __init__(self, default=None, not_in_config = False):
        self.written = False
        self.value = default
        self.isolated = not_in_config
    def __set_name__(self, owner, name):
        self.__name__ = name
    def __get__(self, obj, obj_type=None):
        return self.value
    def __set__(self, obj, value):
        if self.written:
            if value is None:
                pass
            elif type(value) is list and type(self.value) is list and len(set(self.value) - set(value)) <= 0:
                newElems = set(value) - set(self.value)
                if len(newElems) > 0:
                    self.value.extend(newElems)
                else:
                    raise AttributeError('Read-only attribute %s' % self.__name__)
            else:
                raise AttributeError('Read-only attribute %s' % self.__name__)
        elif value is not None:
            self.value = value
            obj.default_values = False
        # Passing none to __set__ locks the variable from changing
        self.written = True

class ConsoleArguments:
    parser = argparse.ArgumentParser(description='Mirrors APT repository efficiently when rsync is unavailable.')
    config = Argument(not_in_config = True)
    source = Argument(def_general.source)
    distro = Argument(def_general.distro)
    destination = Argument(def_general.destination)
    cache = Argument(def_general.cache)
    include = Argument(def_general.whitelist)
    exclude = Argument(def_general.blacklist)
    rpc_listen_all = Argument(def_aria2.listen_all)
    rpc_port = Argument(def_aria2.port)
    rpc_secret = Argument(def_aria2.secret)
    save = Argument(not_in_config = True)
    default_values = True
    def __init__(self):
        self.parser.add_argument('-C', '--config', type=Path, metavar='config_file', help='Path to INI config file.')
        self.parser.add_argument('-u', '--source', type=str, metavar='URL', help='URL to the repository.')
        self.parser.add_argument('-d', '--distro', type=str, help='The distro to get from the source and set at the destination.')
        self.parser.add_argument('-p', '--destination', type=Path, metavar='path', help='Where to store the mirrored.')
        self.parser.add_argument('-c', '--cache', type=Path, metavar='path', help='Where to store the latest file lists from source.')
        self.parser.add_argument('-i', '--include', action='append', type=str, help='Files to include with the mirroring.')
        self.parser.add_argument('-x', '--exclude', action='append', type=str, help='Files to exclude from the mirroring.')
        self.parser.add_argument('-L', '--rpc-listen-all', action='store_true', help='Allow aria2 RPC server to listen on all interfaces (default: localhost).')
        self.parser.add_argument('-P', '--rpc-port', type=int, help='Port of aria2 RPC server.')
        self.parser.add_argument('-S', '--rpc-secret', type=str, help='aria2 RPC protocol secret (security).')
        self.parser.add_argument('-s', '--save', action='store_true', help='Save configured to file (specified via -C).')
    def __setattr__(self, name, value):
        if hasattr(self, name):
            super().__setattr__(name, value)
    def parse(self, args=None):
        return self.parser.parse_args(args=args, namespace=self)
