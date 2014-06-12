from __future__ import absolute_import

import os
import sys

import click
from prettytable import PrettyTable
from requests.exceptions import HTTPError

from . import __version__
from .api import Api, DEFAULT_ENDPOINT

try:
    from urllib import parser as urlparse
except ImportError:
    import urlparse

try:
    import ConfigParser as configparser
except ImportError:
    import configparser

DEFAULT_CONFIG = os.path.join(os.environ['HOME'], '.slipstreamconfig')
DEFAULT_PROFILE = 'slipstream'


def _excepthook(exctype, value, tb):
    if exctype == HTTPError and value.response.status_code == 401:
        e = click.ClickException("Invalid credentials provided. "
                                 "Log in with `slipstream login`.")
        e.show()
    else:
        import traceback
        traceback.print_exception(exctype, value, tb)

sys.excepthook = _excepthook


def printtable(items):
    table = PrettyTable(items[0]._fields)
    table.align = 'l'
    for item in items:
        table.add_row(item)
    click.echo(table)


class URL(click.ParamType):
    name = 'url'

    def convert(self, value, param, ctx):
        if not isinstance(value, tuple):
            url = urlparse.urlparse(value)
            if url.scheme not in ('http', 'https'):
                self.fail('invalid URL scheme (%s).  Only HTTP(S) URLs are '
                          'allowed' % value.scheme, param, ctx)
        return value


class KeyValue(click.ParamType):
    name = 'keyvalue'

    def convert(self, value, param, ctx):
        return tuple(value.split('='))


class Config(object):

    def __init__(self, filename=None, profile=None):
        self.aliases = {
            'launch': 'run image',
            'deploy': 'run deployment',
        }
        self.settings = {
            'endpoint': DEFAULT_ENDPOINT,
        }

        self.filename = DEFAULT_CONFIG if filename is None else filename
        self.profile = DEFAULT_PROFILE if profile is None else profile
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
            if self.profile != DEFAULT_PROFILE:
                raise

    def write_config(self):
        if not self.parser.has_section('alias'):
            self.parser.add_section('alias')
        for alias in self.aliases.iteritems():
            self.parser.set('alias', *alias)

        if not self.parser.has_section(self.profile):
            self.parser.add_section(self.profile)
        for setting in self.settings.iteritems():
            self.parser.set(self.profile, *setting)

        with open(self.filename, 'wb') as fp:
            self.parser.write(fp)
        os.chmod(self.filename, 0600)

    def clear_setting(self, setting):
        self.settings.pop(setting, None)
        try:
            self.parser.remove_option(self.profile, setting)
        except configparser.NoSectionError:
            if self.profile != DEFAULT_PROFILE:
                raise

pass_config = click.make_pass_decorator(Config)


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


def use_profile(ctx, param, value):
    cfg = ctx.ensure_object(Config)
    cfg.profile = value
    return value


def read_config(ctx, param, value):
    cfg = ctx.ensure_object(Config)
    cfg.filename = value or DEFAULT_CONFIG
    try:
        cfg.read_config()
    except configparser.NoSectionError:
        raise click.BadParameter("Profile '%s' does not exists." % cfg.profile,
                                param=cli.params[0])
    return value


@click.command(cls=AliasedGroup)
@click.option('-p', '--profile', metavar='PROFILE', default=DEFAULT_PROFILE,
              callback=use_profile, expose_value=False, is_eager=True,
              help="The section to use from the config file instead of the "
              "default.")
@click.option('-c', '--config', type=click.Path(exists=True, dir_okay=False),
              callback=read_config, expose_value=False,
              help="The config file to use instead of the default.")
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx):
    """SlipStream command line tool"""
    cfg = ctx.obj

    if any(['login' in ctx.args, 'logout' in ctx.args, 'aliases' in ctx.args]):
        return

    # Ask for credentials to the user when (s)he hasn't provided some
    if any([cfg.settings.get('username') is None,
            cfg.settings.get('password') is None]):
        ctx.invoke(login)

    # Attach API object to context for subsequent use
    ctx.obj = Api(cfg.settings['username'], cfg.settings['password'],
                  cfg.settings['endpoint'])


@cli.command()
@pass_config
def aliases(cfg):
    """List currently defined aliases"""
    for alias in sorted(cfg.aliases.iterkeys()):
        click.echo("%s=%s" % (alias, cfg.aliases[alias]))


@cli.command()
@pass_config
def login(cfg):
    """Log in with your slipstream credentials"""
    while True:
        click.echo("Enter your SlipStream credentials.")
        cfg.settings['username'] = click.prompt("Username")
        cfg.settings['password'] = click.prompt("Password (typing will be hidden)",
                                                hide_input=True)

        api = Api(cfg.settings['username'], cfg.settings['password'],
                  cfg.settings['endpoint'])
        if api.verify():
            break
        click.echo("Authentication failed.")

    click.echo("Authentication successful.")
    cfg.write_config()


@cli.command()
@pass_config
def logout(cfg):
    """Clear local authentication credentials"""
    cfg.clear_setting('username')
    cfg.clear_setting('password')
    cfg.write_config()
    click.echo("Local credentials cleared.")


@cli.group()
def list():
    """List resources: apps, images, etc."""
    pass


@list.command('applications', help="list available applications")
@click.pass_obj
def list_applications(api):
    apps = [app for app in api.list_applications()]
    if apps:
        printtable(apps)
    else:
        click.echo("No applications found.")


@list.command('runs', help="list runs")
@click.pass_obj
def list_runs(api):
    runs = [run for run in api.list_runs()]
    if runs:
        printtable(runs)
    else:
        click.echo("No runs found.")


@list.command('virtualmachines')
@click.option('--run', 'run_id', metavar='UUID', type=click.UUID,
              help="The run UUID to filter with.")
@click.option('--cloud', metavar='CLOUD', type=click.STRING,
              help="The cloud service name to filter with.")
@click.option('--status', metavar='STATUS', type=click.STRING,
              help="The status to filter with.")
@click.pass_obj
def list_virtualmachines(api, run_id, cloud, status):
    """List virtual machines filtered according to given options"""
    def filter_func(vm):
        if run_id and vm.run_id != run_id:
            return False
        if cloud and vm.cloud != cloud:
            return False
        if status and vm.status != status:
            return False
        return True

    vms = filter(filter_func, api.list_virtualmachines())
    if vms:
        printtable(vms)
    else:
        click.echo("No virtual machines found matching your criteria.")


@cli.group()
def run():
    """Run modules: image, deployment"""
    pass


@run.command('image')
@click.option('--cloud',
              help="The cloud service to run the image with.")
@click.option('--open', 'should_open', is_flag=True, default=False,
              help="Open the created run in a web browser")
@click.argument('path', metavar='PATH', required=True)
@click.pass_context
def run_image(ctx, cloud, should_open, path):
    """Run the image to the defined cloud"""
    api = ctx.obj
    try:
        run_id = api.run_image(path, cloud)
    except HTTPError as e:
        raise click.ClickException(str(e))

    if should_open:
        ctx.invoke(open_cmd, run_id=run_id)
    else:
        click.echo(run_id)


@run.command('deployment')
@click.option('--cloud', type=KeyValue(), metavar='NODE=CLOUD', nargs=-1)
@click.option('--multiplicity', type=KeyValue(), metavar='NODE=MULTIPLICITY',
              nargs=-1)
@click.option('--open', 'should_open', is_flag=True, default=False,
              help="Open the created run in a web browser.")
@click.argument('path', metavar='PATH', required=True)
@click.pass_obj
def run_deployment(api, cloud, multiplicity, should_open, path):
    """Run a deployment"""
    pass


@cli.command('open')
@click.argument('run_id', metavar='UUID', type=click.UUID)
@click.pass_obj
def open_cmd(api, run_id):
    """Open the given run UUID in a web browser"""
    click.launch("{0}/run/{1}".format(api.endpoint, run_id))


@cli.command()
@click.argument('run_id', metavar='UUID', type=click.UUID)
@click.pass_obj
def terminate(api, run_id):
    """Terminate the given run UUID"""
    try:
        api.terminate(run_id)
    except HTTPError as e:
        raise click.ClickException(str(e))
    click.echo("Run successfully terminated.")


@cli.command()
@click.pass_obj
def usage(api):
    """List current usage and quota for user by cloud service"""
    items = [item for item in api.usage()]
    printtable(items)
