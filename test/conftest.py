from __future__ import unicode_literals

import uuid

from slipstream.cli import models
from slipstream.cli.base import Config

import mock
import pytest
from click.testing import CliRunner

@pytest.yield_fixture(autouse=True)
def ensure_config_is_reset_between_tests():
    # Code that will run before the test.
    Config().reset_config()

    yield  # Run the test case

    # Code that will run after the test.
    Config().reset_config()

@pytest.fixture(autouse=True)
def config_file(monkeypatch, tmpdir):
    config_file = tmpdir.join('config')
    monkeypatch.setattr('slipstream.cli.conf.DEFAULT_CONFIG_FILE',
                        config_file.strpath)
    return config_file

@pytest.fixture(autouse=True)
def cookie_file(monkeypatch, tmpdir):
    cookie_file = tmpdir.join('cookies.txt')
    monkeypatch.setattr('slipstream.cli.conf.DEFAULT_COOKIE_FILE',
                        cookie_file.strpath)
    return cookie_file

@pytest.fixture(scope='function')
def runner():
    return CliRunner()


@pytest.fixture(scope='function')
def cli():
    from slipstream.cli.commands import cli
    return cli


@pytest.fixture(scope='function')
def api(cookie_file):
    from slipstream.cli.api import Api
    return Api(cookie_file=cookie_file.strpath)


@pytest.fixture(scope='function')
def authenticated(request, config_file, cookie_file):
    config_file.write("[slipstream]\n""username = clara\n")
    cookie_file.write("# Netscape HTTP Cookie File\n"
                      "# http://curl.haxx.se/rfc/cookie_spec.html\n"
                      "# This is a generated file!  Do not edit.\n\n"
                      "slipstream.sixsq.com\tFALSE\t/\tFALSE\t\t"
                      "com.sixsq.slipstream.cookie\tcom.sixsq.idtype=local&"
                      "com.sixsq.identifier=clara&"
                      "com.sixsq.expirydate=1403235417973&"
                      "com.sixsq.signature=abcd1234")

    patcher = mock.patch('slipstream.cli.api.Api.login')
    def teardown():
        patcher.stop()
    request.addfinalizer(teardown)
    patcher.start()


@pytest.fixture(scope='function')
def apps():
    return [
        models.App(name="wordpress", type='component', version=3842,
                   path="apps/WordPress/wordpress"),
        models.App(name="ubuntu-14.04", type="component", version=4847,
                   path="examples/images/ubuntu-14.04"),
    ]


@pytest.fixture(scope='function')
def vms():
    return [
        models.VirtualMachine(
            id='a087572b-e368-421a-8a25-ed67fcdfe202',
            cloud="exoscale-ch-gva",
            status="running",
            run_id=uuid.UUID('fa204c53-2d74-4fee-a76e-014e21ca3bd0')),
        models.VirtualMachine(
            id='cac1725a-ee6d-45f4-bbf7-e67c0db7e64e',
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
        models.Usage('exoscale-ch-gva', 1, 2, 0, 0, 0, 0, 20),
        models.Usage('ec2-eu-west',     0, 0, 0, 2, 0, 0, 20),
        models.Usage('All Clouds',      1, 2, 0, 2, 0, 0, 40),
    ]
