# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import configparser
import sys
import uuid

import mock
import pytest
import requests

from slipstream.cli import models


class UnauthorizedError(requests.HTTPError):

    def __init__(self, *args, **kwargs):
        self.response = requests.Response()
        self.response.status_code = 401


class NotFoundError(requests.HTTPError):

    def __init__(self, *args, **kwargs):
        self.response = requests.Response()
        self.response.status_code = 404


class ConflictError(requests.HTTPError):

    def __init__(self, *args, **kwargs):
        self.response = requests.Response()
        self.response.status_code = 409


class TestAlias(object):

    def test_common(self, runner, cli):
        result = runner.invoke(cli, ['aliases'])
        assert result.exit_code == 0
        assert result.output == ("deploy=run deployment\n"
                                 "launch=run image\n")

    def test_defined(self, runner, cli, config_file):
        config_file.write("[alias]\nvms=list virtualmachines")

        result = runner.invoke(cli, ['aliases'])
        assert result.exit_code == 0
        assert result.output == ("deploy=run deployment\n"
                                 "launch=run image\n"
                                 "vms=list virtualmachines\n")

    def test_with_config(self, runner, cli, tmpdir):
        config = tmpdir.join('slipstreamconfig')
        config.write("[alias]\napps=list apps")

        result = runner.invoke(cli, ['--config', config.strpath, 'aliases'])
        assert result.exit_code == 0
        assert result.output == ("apps=list apps\n"
                                 "deploy=run deployment\n"
                                 "launch=run image\n")

    def test_no_config(self, runner, cli):
        result = runner.invoke(cli, ['--config', 'config1', 'aliases'])
        assert result.exit_code == 2


class TestLogin(object):

    def test_no_profile(self, runner, cli):
        result = runner.invoke(cli, ['--profile', 'profile1', 'login'])
        assert result.exit_code == 2
        assert result.exception
        assert "Profile 'profile1' does not exists." in result.output

    def test_no_credentials(self, runner, cli, config_file):
        with mock.patch('slipstream.cli.api.Api.login',
                        side_effect=[UnauthorizedError, None]):
            result = runner.invoke(cli, ['login'],
                                   input=("anonymous\npassword\n"
                                          "clara\ns3cr3t\n"))
        assert result.exit_code == 0
        assert result.output == ("Enter your SlipStream credentials.\n"
                                 "Username: anonymous\n"
                                 "Password (typing will be hidden): \n"
                                 "Authentication failed.\n"
                                 "Enter your SlipStream credentials.\n"
                                 "Username: clara\n"
                                 "Password (typing will be hidden): \n"
                                 "Authentication successful.\n")

        parser = configparser.RawConfigParser()
        parser.read(config_file.strpath)
        assert parser.get('slipstream', 'username') == 'clara'

    def test_prompt_other_command(self, runner, cli, config_file):
        with mock.patch('slipstream.cli.api.Api.login',
                        side_effect=[UnauthorizedError, None]):
            result = runner.invoke(cli, ['list'],
                                   input=("anonymous\npassword\n"
                                          "clara\ns3cr3t\n"))
        assert result.exit_code == 0
        assert result.output.startswith("Enter your SlipStream credentials.\n"
                                        "Username: anonymous\n"
                                        "Password (typing will be hidden): \n"
                                        "Authentication failed.\n"
                                        "Enter your SlipStream credentials.\n"
                                        "Username: clara\n"
                                        "Password (typing will be hidden): \n"
                                        "Authentication successful.\n")

        parser = configparser.RawConfigParser()
        parser.read(config_file.strpath)
        assert parser.get('slipstream', 'username') == 'clara'

    def test_with_credentials_other_command(self, runner, cli, config_file):
        with mock.patch('slipstream.cli.api.Api.login'):
            result = runner.invoke(cli, ['-u', 'alice', '-p', 'h4x0r', 'list'])

        assert result.exit_code == 0
        assert "Authentication successful.\n" not in result.output

        parser = configparser.RawConfigParser()
        parser.read(config_file.strpath)
        assert parser.get('slipstream', 'username') == 'alice'

    def test_with_credentials(self, runner, cli, config_file):
        with mock.patch('slipstream.cli.api.Api.login'):
            result = runner.invoke(cli, ['login'], input=("alice\nh4x0r\n"))

        assert result.exit_code == 0
        assert result.output == ("Enter your SlipStream credentials.\n"
                                 "Username: alice\n"
                                 "Password (typing will be hidden): \n"
                                 "Authentication successful.\n")

        parser = configparser.RawConfigParser()
        parser.read(config_file.strpath)
        assert parser.get('slipstream', 'username') == 'alice'

    def test_with_config_and_profile(self, runner, cli, tmpdir):
        config = tmpdir.join('slipstreamconfig')
        config.write("[profile1]\nendpoint = https://example.com")

        with mock.patch('slipstream.cli.api.Api.login'):
            result = runner.invoke(cli, ['-P', 'profile1', '-c', config.strpath,
                                         'login'],
                                   input=("bob\nstaple horse\n"))

        assert result.exit_code == 0
        assert result.output == ("Enter your SlipStream credentials.\n"
                                 "Username: bob\n"
                                 "Password (typing will be hidden): \n"
                                 "Authentication successful.\n")

        parser = configparser.RawConfigParser()
        parser.read(config.strpath)
        assert parser.get('profile1', 'username') == 'bob'
        assert parser.has_section('slipstream') is False

    def test_with_options(self, runner, cli, config_file):
        with mock.patch('slipstream.cli.api.Api.login'):
            result = runner.invoke(cli, ['login',
                                         '-u', u'sébastien',
                                         '-p', 'not_secure_at_all',
                                         '--endpoint', 'http://127.0.0.1:8080'])

        assert result.exit_code == 0
        parser = configparser.RawConfigParser()
        parser.read(config_file.strpath, encoding='utf8')
        assert parser.get('slipstream', 'username') == u'sébastien'
        assert parser.get('slipstream', 'endpoint') == 'http://127.0.0.1:8080'


class TestLogout(object):

    def test_no_credentials(self, runner, cli):
        result = runner.invoke(cli, ['logout'])
        assert result.exit_code == 0
        assert result.output == "Local credentials cleared.\n"

    @pytest.mark.usefixtures("authenticated")
    def test_with_credentials(self, runner, cli, cookie_file):
        result = runner.invoke(cli, ['logout'])
        assert result.exit_code == 0
        assert result.output == "Local credentials cleared.\n"
        if sys.version_info < (2, 7, 7):
            assert cookie_file.read() == (
                "# Netscape HTTP Cookie File\n"
                "# http://www.netscape.com/newsref/std/cookie_spec.html\n"
                "# This is a generated file!  Do not edit.\n\n")
        else:
            assert cookie_file.read() == (
                "# Netscape HTTP Cookie File\n"
                "# http://curl.haxx.se/rfc/cookie_spec.html\n"
                "# This is a generated file!  Do not edit.\n\n")


@pytest.mark.usefixtures('authenticated')
class TestListApplications(object):

    def test_list_all(self, runner, cli, apps):
        with mock.patch('slipstream.cli.api.Api.list_applications',
                        return_value=iter(apps)):
            result = runner.invoke(cli, ['list', 'applications'])

        assert result.exit_code == 0
        assert 'wordpress' in result.output
        assert 'ubuntu-12.04' in result.output

    def test_no_apps(self, runner, cli):
        with mock.patch('slipstream.cli.api.Api.list_applications',
                        return_value=iter([])):
            result = runner.invoke(cli, ['list', 'applications'])

        assert result.exit_code == 0
        assert result.output == "No applications found.\n"


@pytest.mark.usefixtures('authenticated')
class TestListModules(object):

    def test_list_all(self, runner, cli, apps):
        with mock.patch('slipstream.cli.api.Api.list_modules',
                        return_value=iter(apps)):
            result = runner.invoke(cli, ['list', 'modules'])

        assert result.exit_code == 0
        assert 'wordpress' in result.output
        assert 'ubuntu-12.04' in result.output

    def test_empty(self, runner, cli):
        with mock.patch('slipstream.cli.api.Api.list_modules',
                        return_value=iter([])):
            result = runner.invoke(cli, ['list', 'modules'])

        assert result.exit_code == 0
        assert result.output == "No modules found matching your criteria.\n"

    def test_with_filter(self, runner, cli, apps):
        with mock.patch('slipstream.cli.api.Api.list_modules',
                        return_value=iter(apps)):
            result = runner.invoke(cli, ['list', 'modules', '-k', 'image'])

        assert result.exit_code == 0
        assert 'wordpress' not in result.output
        assert 'ubuntu-12.04' in result.output

        with mock.patch('slipstream.cli.api.Api.list_modules',
                        return_value=iter(apps)):
            result = runner.invoke(cli, ['list', 'modules', '--type=deployment'])

        assert result.exit_code == 0
        assert 'wordpress' in result.output
        assert 'ubuntu-12.04' not in result.output


@pytest.mark.usefixtures('authenticated')
class TestListRuns(object):

    def test_list_all(self, runner, cli, runs):
        with mock.patch('slipstream.cli.api.Api.list_runs',
                        return_value=iter(runs)):
            result = runner.invoke(cli, ['list', 'runs'])

        assert result.exit_code == 0
        assert '3fd93072-fcef-4c03-bdec-0cb2b19699e2' in result.output
        assert 'bd871bcb-a7aa-4c2a-acbe-38722a388b6e' in result.output
        assert '85127a28-455a-44a4-bba3-ca56bfe6858e' in result.output

    def test_no_runs(self, runner, cli):
        with mock.patch('slipstream.cli.api.Api.list_runs',
                        return_value=iter([])):
            result = runner.invoke(cli, ['list', 'runs'])

        assert result.exit_code == 0
        assert result.output == "No runs found.\n"


@pytest.mark.usefixtures('authenticated')
class TestListVirtualMachines(object):

    def test_list_all(self, runner, cli, vms):
        with mock.patch('slipstream.cli.api.Api.list_virtualmachines',
                        return_value=iter(vms)):
            result = runner.invoke(cli, ['list', 'virtualmachines'])

        assert result.exit_code == 0
        assert 'a087572b-e368-421a-8a25-ed67fcdfe202' in result.output
        assert 'cac1725a-ee6d-45f4-bbf7-e67c0db7e64e' in result.output

    def test_filter_by_run(self, runner, cli, vms):
        with mock.patch('slipstream.cli.api.Api.list_virtualmachines',
                        return_value=iter(vms)):
            result = runner.invoke(cli, ['list', 'virtualmachines', '--run',
                                         'fa204c53-2d74-4fee-a76e-014e21ca3bd0'])

        assert result.exit_code == 0
        assert 'a087572b-e368-421a-8a25-ed67fcdfe202' in result.output
        assert 'cac1725a-ee6d-45f4-bbf7-e67c0db7e64e' not in result.output

    def test_filter_by_cloud(self, runner, cli, vms):
        with mock.patch('slipstream.cli.api.Api.list_virtualmachines',
                        return_value=iter(vms)):
            result = runner.invoke(cli, ['list', 'virtualmachines',
                                         '--cloud', 'ec2-eu-west-1'])

        assert result.exit_code == 0
        assert 'a087572b-e368-421a-8a25-ed67fcdfe202' not in result.output
        assert 'cac1725a-ee6d-45f4-bbf7-e67c0db7e64e' in result.output

    def test_filter_by_status(self, runner, cli, vms):
        with mock.patch('slipstream.cli.api.Api.list_virtualmachines',
                        return_value=iter(vms)):
            result = runner.invoke(cli, ['list', 'virtualmachines',
                                         '--status', 'running'])

        assert result.exit_code == 0
        assert 'a087572b-e368-421a-8a25-ed67fcdfe202' in result.output
        assert 'cac1725a-ee6d-45f4-bbf7-e67c0db7e64e' not in result.output

    def test_multiple_filters(self, runner, cli, vms):
        with mock.patch('slipstream.cli.api.Api.list_virtualmachines',
                        return_value=iter(vms)):
            result = runner.invoke(cli, ['list', 'virtualmachines',
                                         '--cloud', 'exoscale-ch-gva',
                                         '--status', 'running'])

        assert result.exit_code == 0
        assert 'a087572b-e368-421a-8a25-ed67fcdfe202' in result.output
        assert 'cac1725a-ee6d-45f4-bbf7-e67c0db7e64e' not in result.output

    def test_no_results(self, runner, cli):
        with mock.patch('slipstream.cli.api.Api.list_virtualmachines',
                        return_value=iter([])):
            result = runner.invoke(cli, ['list', 'virtualmachines'])

        assert result.exit_code == 0
        assert result.output == ("No virtual machines found matching "
                                 "your criteria.\n")


@pytest.mark.usefixtures("authenticated")
class TestBuildImage(object):

    def test_default(self, runner, cli):
        run_id = uuid.uuid4()

        with mock.patch('slipstream.cli.api.Api.build_image',
                        return_value=run_id):
            result = runner.invoke(cli, ['build', 'clara/centos-6'])

        assert result.exit_code == 0
        assert result.output == "%s\n" % run_id

    def test_with_cloud(self, runner, cli):
        run_id = uuid.uuid4()

        with mock.patch('slipstream.cli.api.Api.build_image',
                        return_value=run_id):
            result = runner.invoke(cli, ['build', 'clara/centos-6',
                                         '--cloud=cloud1'])

        assert result.exit_code == 0
        assert result.output == "%s\n" % run_id


@pytest.mark.usefixtures('authenticated')
class TestRunImage(object):

    def test_default(self, runner, cli):
        run_id = uuid.uuid4()

        with mock.patch('slipstream.cli.api.Api.run_image',
                        return_value=run_id):
            result = runner.invoke(cli, ['run', 'image', 'clara/centos-6'])

        assert result.exit_code == 0
        assert result.output == "%s\n" % run_id

    def test_with_cloud(self, runner, cli):
        run_id = uuid.uuid4()

        with mock.patch('slipstream.cli.api.Api.run_image',
                        return_value=run_id):
            result = runner.invoke(cli, ['run', 'image', 'clara/centos-6',
                                         '--cloud=cloud1'])

        assert result.exit_code == 0
        assert result.output == "%s\n" % run_id


@pytest.mark.usefixtures('authenticated')
class TestRunDeployment(object):

    def test_default(self, runner, cli):
        run_id = uuid.uuid4()

        with mock.patch('slipstream.cli.api.Api.run_deployment',
                        return_value=run_id):
            result = runner.invoke(cli, ['run', 'deployment', 'clara/wordpress'])

        assert result.exit_code == 0
        assert result.output == "%s\n" % run_id

    def test_with_params(self, runner, cli):
        run_id = uuid.uuid4()

        with mock.patch('slipstream.cli.api.Api.run_deployment',
                        return_value=run_id):
            result = runner.invoke(cli, ['run', 'deployment',
                                         'wp:cloud=cloud1', 'wp:multiplicity=2',
                                         'clara/wordpress'])

        assert result.exit_code == 0
        assert result.output == "%s\n" % run_id


@pytest.mark.usefixtures('authenticated')
class TestPublish(object):

    app = models.App(name='foo', type='image', version=42, path='examples/foo')

    def test_no_version(self, runner, cli):
        with mock.patch('slipstream.cli.api.Api.publish'):
            with mock.patch('slipstream.cli.api.Api.get_module',
                            return_value=self.app):
                result = runner.invoke(cli, ['publish', 'foo'])

        assert result.exit_code == 0
        assert result.output == "Module 'foo' #42 published.\n"

    def test_with_version(self, runner, cli):
        with mock.patch('slipstream.cli.api.Api.publish') as patcher:
            result = runner.invoke(cli, ['publish', 'foo', '42'])
            patcher.assert_called_with('foo/42')

        assert result.exit_code == 0
        assert result.output == "Module 'foo' #42 published.\n"

    def test_not_exists(self, runner, cli):
        with mock.patch('slipstream.cli.api.Api.publish',
                        side_effect=NotFoundError):
            result = runner.invoke(cli, ['publish', 'foo', '69'])

        assert result.exit_code == 1
        assert result.exception
        assert result.output == "Error: Module 'foo' #69 doesn't exists.\n"

    def test_already_published(self, runner, cli):
        with mock.patch('slipstream.cli.api.Api.publish',
                        side_effect=ConflictError):
            result = runner.invoke(cli, ['publish', 'foo', '69'])

        assert result.exit_code == 0
        assert result.output == "Module 'foo' #69 is already published.\n"


@pytest.mark.usefixtures('authenticated')
class TestUnpublish(object):

    app = models.App(name='foo', type='image', version=42, path='examples/foo')

    def test_no_version(self, runner, cli):
        with mock.patch('slipstream.cli.api.Api.unpublish'):
            with mock.patch('slipstream.cli.api.Api.get_module',
                            return_value=self.app):
                result = runner.invoke(cli, ['unpublish', 'foo'])

        assert result.exit_code == 0
        assert result.output == "Module 'foo' #42 unpublished.\n"

    def test_with_version(self, runner, cli):
        with mock.patch('slipstream.cli.api.Api.unpublish') as patcher:
            result = runner.invoke(cli, ['unpublish', 'foo', '42'])
            patcher.assert_called_with('foo/42')

        assert result.exit_code == 0
        assert result.output == "Module 'foo' #42 unpublished.\n"

    def test_not_exists(self, runner, cli):
        with mock.patch('slipstream.cli.api.Api.unpublish',
                        side_effect=NotFoundError):
            result = runner.invoke(cli, ['unpublish', 'foo', '69'])

        assert result.exit_code == 1
        assert result.exception
        assert result.output == "Error: Module 'foo' #69 doesn't exists.\n"


@pytest.mark.usefixtures('authenticated')
class TestDeleteModule(object):

    def test_no_version(self, runner, cli):
        module = 'module/foo'
        with mock.patch('slipstream.cli.api.Api.delete_module'):
            result = runner.invoke(cli, ['delete', module])

        assert result.exit_code == 0
        assert result.output == "Deleted module %s\n" % module

    def test_with_version(self, runner, cli):
        module = 'module/foo'
        version = '123'
        with mock.patch('slipstream.cli.api.Api.delete_module'):
            result = runner.invoke(cli, ['delete', module, version])

        assert result.exit_code == 0
        assert result.output == "Deleted module %s/%s\n" % (module, version)

    def test_not_exists(self, runner, cli):
        module = 'foo'
        with mock.patch('slipstream.cli.api.Api.delete_module',
                        side_effect=NotFoundError):
            result = runner.invoke(cli, ['delete', module])

        assert result.exit_code == 1
        assert result.exception
        assert result.output == "Error: Module %s done not exist.\n" % module

