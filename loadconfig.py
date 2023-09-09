#!/usr/bin/env python3

# python 3.9 and onward required

from defaults import def_general, def_aria2
from abc import ABC, abstractmethod
from pathtools import changedir
import configparser
from pathlib import Path
import json

class OptionException(Exception):
    pass

class OptionItem:
    def __init__(self, var_type=str, default=None):
        self.vartype = var_type
        self.__default__ = default
    def __set_name__(self, owner, name):
        self.__name__ = name
    def __get__(self, obj, objtype=None):
        try:
            strvalue = obj.__section__[self.__name__]
            if self.vartype is dict or self.vartype is list:
                return json.loads(strvalue)
            else:
                return self.vartype(strvalue)
        except KeyError:
            self.update_value(obj, self.__default__)
            return self.__default__
    def __set__(self, obj, value):
        if value is None:
            self.update_value(obj, self.__default__)
        elif type(value) == '':
            obj.__section__[self.__name__] = ''
        elif type(value) is not self.vartype:
            raise ValueError('Provided vaue is not of type <%s>.' % self.vartype.__name__)
        else:
            self.update_value(obj, value)
    def update_value(self, obj, value):
        if value is None:
            obj.__section__[self.__name__] = ''
        elif self.vartype is dict or self.vartype is list:
            obj.__section__[self.__name__] = json.dumps(value)
        else:
            obj.__section__[self.__name__] = str(value)
        obj.unsaved = True

class Options(ABC):
    """Base options loader frontend of ConfigParser"""
    config_file = None
    unsaved = False
    __parent__ = None
    __section__ = None
    def __init__(self, obj = None, section_alt_name = None):
        super(Options, self).__init__()
        self.unsaved = False
        if obj.__class__.__name__.endswith('Options'):
            self.__parent__ = obj.__parent__
            self.config_file = obj.config_file
        elif type(obj) is configparser.ConfigParser:
            self.__parent__ = obj
            self.config_file = None
        else:
            self.__parent__ = configparser.ConfigParser()
            if obj is None:
                pass
            elif type(obj) is str or type(obj) is Path:
                self.config_file = Path(obj)
                if self.config_file.is_file():
                    with self.config_file.open('r') as f:
                        self.__parent__.read_file(f)
            else:
                raise OptionException('Unknown given object.')
        if section_alt_name is None:
            # replace '_' with ' '
            section = self.__class__.__name__.removesuffix('Options').replace('_', ' ')
        else:
            section = section_alt_name
        if len(section) > 0:
            if not section in self.__parent__:
                self.unsaved = True
                self.__parent__.add_section(section)
            self.__section__ = self.__parent__[section]
            self.prepare_variables()
        else:
            raise OptionException('Undefined section.')
    def set_config_file(self, path):
        self.config_file = Path(path)
    def flush(self, force=False):
        if self.config_file is None:
            raise OptionException('Missing config file')
        if force:
            path = changedir(self.config_file, '..')
            if not path.is_dir():
                path.mkdir(0o755, True, True)
        with self.config_file.open('w') as f:
            self.__parent__.write(f)
        self.unsaved = False
    def load(self, force=False):
        if self.config_file is None:
            raise OptionException('Missing config file')
        if (self.unsaved & force) or ((not self.unsaved) & force):
            with self.config_file.open('r') as f:
                self.__parent__.read_file(f)
                self.unsaved = False
        else:
            raise OptionException('There are unsaved configurations!')
    @abstractmethod
    def prepare_variables(self):
        pass

class generalOptions(Options):
    source = OptionItem(default=def_general.source)
    distro = OptionItem(default=def_general.distro)
    destination = OptionItem(var_type=Path, default=def_general.destination)
    cache = OptionItem(var_type=Path, default=def_general.cache)
    whitelist = OptionItem(var_type=list, default=def_general.whitelist)
    blacklist = OptionItem(var_type=list, default=def_general.blacklist)
    def prepare_variables(self):
        src = self.source
        d = self.distro
        dst = self.destination
        c = self.cache
        w = self.whitelist
        b = self.blacklist

class aria2Options(Options):
    listen_all = OptionItem(default=def_aria2.listen_all)
    port = OptionItem(var_type=int, default=def_aria2.port)
    secret = OptionItem(default=def_aria2.secret)
    def prepare_variables(self):
        l = self.listen_all
        p = self.port
        s = self.secret
