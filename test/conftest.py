import os
import uuid

import mock
import pytest

from click.testing import CliRunner
from slipstream.cli import models


@pytest.fixture(scope='function')
def runner():
    return CliRunner()


@pytest.fixture(scope='function')
def cli():
    from slipstream.cli.base import cli
    return cli


@pytest.fixture(scope='function')
def api():
    from slipstream.cli import api
    return api.Api(username='clara', password='s3cr3t')


@pytest.fixture(autouse=True)
def default_config_file(request, monkeypatch):
    filename = '.slipstreamconfig'
    monkeypatch.setattr('slipstream.cli.base.DEFAULT_CONFIG', filename)
    return filename


@pytest.fixture(autouse=True)
def isolated_filesystem(request, tmpdir):
    cwd = os.getcwd()
    tmpdir.chdir()

    def teardown():
        os.chdir(cwd)
    request.addfinalizer(teardown)


@pytest.fixture(scope='function')
def verified_auth(request, default_config_file, isolated_filesystem):
    with open(default_config_file, 'wb') as f:
        f.write("[slipstream]\nusername = clara\npassword = s3cr3t\n")

    patcher = mock.patch('slipstream.cli.api.Api.verify', return_value=True)
    def teardown():
        patcher.stop()
    request.addfinalizer(teardown)
    patcher.start()


@pytest.fixture(scope='function')
def apps():
    return [
        models.App(name="wordpress", type='deployment', version=478,
                   path="examples/tutorials/wordpress/wordpress/478"),
        models.App(name="ubuntu-12.04", type="image", version=480,
                   path="examples/images/ubuntu-12.04/480"),
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
