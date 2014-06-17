from __future__ import unicode_literals

import uuid

from slipstream.cli import models

import mock
import pytest
from click.testing import CliRunner


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
    return Api()


@pytest.fixture(scope='function')
def authenticated(request, default_config):
    default_config.write("[slipstream]\n"
                         "username = clara\n"
                         "token = s3cr3t\n")

    patcher = mock.patch('slipstream.cli.api.Api.login', return_value='s3cr3t')
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


@pytest.fixture(scope='function')
def runs():
    return [
        models.Run(
            id=uuid.UUID('3fd93072-fcef-4c03-bdec-0cb2b19699e2'),
            module='examples/tutorials/wordpress/wordpress/478',
            status='running',
            started_at='2014-06-13 12:09:47.202 UTC',
            cloud='exoscale-ch-gva'),
        models.Run(
            id=uuid.UUID('bd871bcb-a7aa-4c2a-acbe-38722a388b6e'),
            module='examples/images/centos-6/479',
            status='running',
            started_at='2014-06-12 08:55:43.12 UTC',
            cloud='ec2-eu-west'),
        models.Run(
            id=uuid.UUID('85127a28-455a-44a4-bba3-ca56bfe6858e'),
            module='examples/images/centos-6/479',
            status='aborted',
            started_at='2014-06-12 08:48:23.677 UTC',
            cloud='exoscale-ch-gva')
    ]


@pytest.fixture(scope='function')
def usage():
    return [
        models.Usage('exoscale-ch-gva', 1, 20),
        models.Usage('ec2-eu-west', 0, 20),
    ]
