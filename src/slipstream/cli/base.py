from __future__ import absolute_import, unicode_literals

import os
import stat

import click
import six

from six.moves import configparser

from . import conf


class Config(object):

    def __init__(self, filename=None, profile=None):
        self.aliases = {
            'launch': 'run image',
            'deploy': 'run deployment',
        }
        self.settings = {
            'endpoint': conf.DEFAULT_ENDPOINT,
        }

        self.filename = conf.DEFAULT_CONFIG if filename is None else filename
        self.profile = conf.DEFAULT_PROFILE if profile is None else profile
        self.parser = configparser.RawConfigParser()

    def read_config(self):
        self.parser.read([self.filename])
        try:
            self.aliases.update(self.parser.items('alias'))
        except configparser.NoSectionError:
            pass
        try:
            self.settings.update(self.parser.items(self.profile))
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
        for setting in six.iteritems(self.settings):
            self.parser.set(self.profile, *setting)

        with open(self.filename, 'w') as fp:
            self.parser.write(fp)
        os.chmod(self.filename, stat.S_IRUSR)

    def clear_setting(self, setting):
        self.settings.pop(setting, None)
        try:
            self.parser.remove_option(self.profile, setting)
        except configparser.NoSectionError:
            if self.profile != conf.DEFAULT_PROFILE:
                raise


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
