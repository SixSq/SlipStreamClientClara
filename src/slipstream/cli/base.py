from __future__ import absolute_import, unicode_literals

import codecs
import configparser
import os
import stat
import threading
import weakref

import six

import click

from . import conf


class PersistentSingleton(type):
    ''' This class is meant to be used as a metaclass to transform a class into a singleton '''

    _instances = {} #weakref.WeakValueDictionary()
    _singleton_lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._singleton_lock:
            if cls not in cls._instances:
                instance = super(PersistentSingleton, cls).__call__(*args, **kwargs)
                cls._instances[cls] = instance
                return instance
            return cls._instances[cls]


class Config(object):

    __metaclass__ = PersistentSingleton

    def __init__(self, filename=None, profile=None, batch_mode=False):
        self.aliases = {
            'ls': 'list',
            'alias': 'aliases',
            'app-store': 'appstore',
            'launch': 'run',
            'deploy': 'run',
            'vms': 'virtualmachines',
            'virtual-machines': 'virtualmachines'
        }

        self.settings = {
            'endpoint': conf.DEFAULT_ENDPOINT,
            'insecure': False
        }

        self._profile = None

        self.filename = conf.DEFAULT_CONFIG_FILE if filename is None else filename
        self.parser = configparser.ConfigParser(interpolation=None)
        self.profile = profile
        self.batch_mode = batch_mode

    @property
    def profile(self):
        return conf.DEFAULT_PROFILE if self._profile is None else self._profile

    @profile.setter
    def profile(self, value):
        self._profile = value if value is not None else conf.DEFAULT_PROFILE
        self.set_default_cookie_file()

    def set_default_cookie_file(self):
        cookie_file_path = conf.COOKIE_FILE_PATH + \
                           conf.COOKIE_FILE_NAME_FORMAT.format(profile=self.profile)
        self.settings['cookie_file'] = os.path.expanduser(cookie_file_path)

    @staticmethod
    def parse_option(value):
        if value is not None:
            if value.lower() in ('1', 'yes', 'true', 'on'):
                return True
            elif value.lower() in ('0', 'no', 'false', 'off'):
                return False
        return value

    def reset_config(self):
        self.__init__()

    def read_config(self):
        if os.path.isfile(self.filename):
            with codecs.open(self.filename, encoding='utf8') as fp:
                self.parser.read_file(fp)
        try:
            self.aliases.update(self.parser.items('alias'))
        except configparser.NoSectionError:
            pass
        try:
            for key, value in self.parser.items(self.profile):
                self.settings[key] = self.parse_option(value)
        except configparser.NoSectionError:
            if self.profile != conf.DEFAULT_PROFILE:
                raise

    def write_config(self):
        if not self.parser.has_section('alias'):
            self.parser.add_section('alias')
        for alias in six.iteritems(self.aliases):
            self.parser.set('alias', *alias)

        if not self.parser.has_section(self.profile):
            self.parser.add_section(self.profile)
        for option, value in six.iteritems(self.settings):
            self.parser.set(self.profile, option, str(value))

        # Create the $HOME/.slipstream dir if it doesn't exist
        config_dir = os.path.dirname(self.filename)
        if not os.path.isdir(config_dir):
            os.mkdir(config_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        # Save configuration into file
        with codecs.open(self.filename, 'wb', 'utf8') as fp:
            self.parser.write(fp)
        os.chmod(self.filename, stat.S_IRUSR | stat.S_IWUSR)

    def clear_setting(self, setting):
        self.settings.pop(setting, None)
        try:
            self.parser.remove_option(self.profile, setting)
        except configparser.NoSectionError:
            if self.profile != conf.DEFAULT_PROFILE:
                raise

pass_config = click.make_pass_decorator(Config, True)


class AliasedGroup(click.Group):
    """This subclass of a group supports looking up aliases in a config
    file and with a bit of magic.
    """

    def get_command(self, ctx, cmd_name):
        # Step one: bulitin commands as normal
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv

        # Step two: find the config object and ensure it's there.
        cfg = ctx.ensure_object(Config)

        # Step three: lookup an explicit command alias in the config
        if cmd_name in cfg.aliases:
            actual_cmd = cfg.aliases[cmd_name]
            return self.find_command(ctx, actual_cmd)

    def find_command(self, ctx, cmd_name):
        cmd_names = cmd_name.split(' ')
        root = self
        for _cmd_name in cmd_names:
            root = click.Group.get_command(root, ctx, _cmd_name)
            if root is None:
                return
        return root
