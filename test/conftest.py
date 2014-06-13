from __future__ import unicode_literals

import uuid

import mock
import pytest

from click.testing import CliRunner
from slipstream.cli import models


@pytest.fixture(autouse=True)
def default_config(monkeypatch, tmpdir):
    config = tmpdir.join('.slipstreamconfig')
    monkeypatch.setattr('slipstream.cli.conf.DEFAULT_CONFIG', config.strpath)
    return config


@pytest.fixture(scope='function')
def runner():
    return CliRunner()


@pytest.fixture(scope='function')
def cli():
    from slipstream.cli.commands import cli
    return cli


@pytest.fixture(scope='function')
def api():
    from slipstream.cli.api import Api
    return Api(username='clara', password='s3cr3t')


@pytest.fixture(scope='function')
def authenticated(request, default_config):
    default_config.write("[slipstream]\n"
                         "username = clara\n"
                         "password = s3cr3t\n")

    patcher = mock.patch('slipstream.cli.api.Api.verify', return_value=True)
    def teardown():
        patcher.stop()
    request.addfinalizer(teardown)
    patcher.start()


@pytest.fixture(scope='function')
def apps():
    return [
        models.App(name="wordpress", type='deployment', version=478,
                   path="examples/tutorials/wordpress/wordpress"),
        models.App(name="ubuntu-12.04", type="image", version=480,
                   path="examples/images/ubuntu-12.04"),
    ]


@pytest.fixture(scope='function')
def vms():
    return [
        models.VirtualMachine(
            id=uuid.UUID('a087572b-e368-421a-8a25-ed67fcdfe202'),
            cloud="exoscale-ch-gva",
            status="running",
            run_id=uuid.UUID('fa204c53-2d74-4fee-a76e-014e21ca3bd0')),
        models.VirtualMachine(
            id=uuid.UUID('cac1725a-ee6d-45f4-bbf7-e67c0db7e64e'),
            cloud="ec2-eu-west-1",
            status="terminated",
            run_id=uuid.UUID('e908ffdf-8445-4990-a781-e6f7d5e7044d')),
    ]
