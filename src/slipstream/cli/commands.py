from __future__ import absolute_import, unicode_literals

import configparser
import sys
import traceback

import six
from requests.exceptions import HTTPError

import click
from prettytable import PrettyTable

from . import __version__, types
from .api import Api
from .base import AliasedGroup, Config, pass_config
from .log import logger

try:
    from defusedxml import cElementTree as etree
except ImportError:
    from defusedxml import ElementTree as etree

def _excepthook(exctype, value, tb):
    if exctype == HTTPError:
        if value.response.status_code == 401:
            logger.fatal("Authentication token expired. "
                        "Log in with `slipstream login`.")
        elif value.response.status_code == 403:
            logger.fatal("Invalid credentials provided. "
                        "Log in with `slipstream login`.")
        elif 'xml' in value.response.headers['content-type']:
            root = etree.fromstring(value.response.text)
            logger.fatal(root.text)
        else:
            logger.fatal(str(value))
    else:
        logger.fatal(str(value))
        out = six.StringIO()
        traceback.print_exception(exctype, value, tb, file=out)
        logger.info(out.getvalue())

sys.excepthook = _excepthook


def printtable(items):
    table = PrettyTable(items[0]._fields)
    table.align = 'l'
    for item in items:
        table.add_row(item)
    click.echo(table)


def use_profile(ctx, param, value):
    cfg = ctx.ensure_object(Config)
    if value is not None:
        cfg.profile = value
    return value


def read_config(ctx, param, value):
    cfg = ctx.ensure_object(Config)
    if value is not None:
        cfg.filename = value
    try:
        cfg.read_config()
    except configparser.NoSectionError:
        raise click.BadParameter("Profile '%s' does not exists." % cfg.profile,
                                param=cli.params[0])
    return value


def config_set(ctx, param, value):
    cfg = ctx.ensure_object(Config)
    if value is not None:
        cfg.settings[param.name] = value
    return value


@click.command(cls=AliasedGroup)
@click.option('-P', '--profile', metavar='PROFILE',
              callback=use_profile, expose_value=False, is_eager=True,
              help="The section to use from the config file instead of the "
              "default.")
@click.option('-c', '--config', type=click.Path(exists=True, dir_okay=False),
              callback=read_config, expose_value=False,
              help="The config file to use instead of the default.")
@click.option('-u', '--username', metavar='USERNAME',
              callback=config_set, expose_value=False,
              help="The SlipStream username to connect with")
@click.option('-p', '--password', metavar='PASSWORD',
              help="The SlipStream password to connect with")
@click.option('-e', '--endpoint', type=types.URL(), metavar='URL',
              callback=config_set, expose_value=False,
              help='The SlipStream endpoint to use')
@click.option('-q', '--quiet', 'quiet', count=True, help="Give less output. "
              "Option is additive, and can be used up to 3 times.")
@click.option('-v', '--verbose', 'verbose', count=True, help="Give more output. "
              "Option is additive, and can be used up to 3 times.")
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, password, quiet, verbose):
    """SlipStream command line tool"""
    # Configure logging
    level = 1  # Notify
    level += verbose
    level -= quiet
    logger.set_level(4 - level)

    # Attach Config object to context for subsequent use
    cfg = ctx.obj

    if any(['login' in ctx.args, 'logout' in ctx.args, 'aliases' in ctx.args]):
        return

    # Ask for credentials to the user when (s)he hasn't provided some
    if 'token' not in cfg.settings:
        ctx.invoke(login, password)

    # Attach Api object to context for subsequent use
    ctx.obj = Api(cfg.settings['endpoint'], cfg.settings['token'])


@cli.command()
@pass_config
def aliases(cfg):
    """List currently defined aliases"""
    for alias in sorted(six.iterkeys(cfg.aliases)):
        click.echo("%s=%s" % (alias, cfg.aliases[alias]))


@cli.command()
@click.option('-u', '--username', metavar='USERNAME',
              callback=config_set, expose_value=False,
              help="The SlipStream username to connect with")
@click.option('-p', '--password', metavar='PASSWORD',
              help="The SlipStream password to connect with")
@click.option('-e', '--endpoint', type=types.URL(), metavar='URL',
              callback=config_set, expose_value=False,
              help='The SlipStream endpoint to use')
@pass_config
def login(cfg, password):
    """Log in with your slipstream credentials"""
    should_prompt = True
    api = Api(cfg.settings['endpoint'])
    username = cfg.settings.get('username')

    if username and password:
        try:
            token = api.login(username, password)
        except HTTPError as e:
            if e.response.status_code != 401:
                raise
            logger.warning("Invalid credentials provided.")
        else:
            should_prompt = False

    while should_prompt:
        logger.notify("Enter your SlipStream credentials.")
        username = click.prompt("Username")
        password = click.prompt("Password (typing will be hidden)",
                                hide_input=True)

        try:
            token = api.login(username, password)
        except HTTPError as e:
            if e.response.status_code != 401:
                raise
            logger.error("Authentication failed.")
        else:
            cfg.settings['username'] = username
            should_prompt = False

    logger.notify("Authentication successful.")
    cfg.settings['token'] = token
    cfg.write_config()
    logger.info("Local credentials saved.")


@cli.command()
@pass_config
def logout(cfg):
    """Clear local authentication credentials"""
    cfg.clear_setting('username')
    cfg.clear_setting('token')
    cfg.write_config()
    logger.notify("Local credentials cleared.")


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
        logger.warning("No applications found.")


@list.command('runs', help="list runs")
@click.pass_obj
def list_runs(api):
    runs = [run for run in api.list_runs()]
    if runs:
        printtable(runs)
    else:
        logger.warning("No runs found.")


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

    vms = [vm for vm in api.list_virtualmachines() if filter_func(vm)]
    if vms:
        printtable(vms)
    else:
        logger.warning("No virtual machines found matching your criteria.")


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
    run_id = api.run_image(path, cloud)
    click.echo(run_id)
    if should_open:
        ctx.invoke(open_cmd, run_id=run_id)


@run.command('deployment')
@click.option('--open', 'should_open', is_flag=True, default=False,
              help="Open the created run in a web browser.")
@click.argument('params', type=types.NodeKeyValue(), metavar='NODE:KEY=VALUE',
                nargs=-1, required=False)
@click.argument('path', metavar='PATH', nargs=1, required=True)
@click.pass_context
def run_deployment(ctx, should_open, params, path):
    """Run a deployment"""
    api = ctx.obj
    run_id = api.run_deployment(path, params)
    click.echo(run_id)
    if should_open:
        ctx.invoke(open_cmd, run_id=run_id)


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
    api.terminate(run_id)
    logger.info("Run successfully terminated.")


@cli.command()
@click.pass_obj
def usage(api):
    """List current usage and quota for user by cloud service"""
    items = [item for item in api.usage()]
    printtable(items)
