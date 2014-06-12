from __future__ import unicode_literals

from six.moves import configparser

import mock
import pytest


class TestAlias(object):

    def test_common(self, runner, cli):
        result = runner.invoke(cli, ['aliases'])
        assert result.exit_code == 0
        assert result.output == ("deploy=run deployment\n"
                                 "launch=run image\n")

    def test_defined(self, runner, cli, default_config):
        default_config.write("[alias]\nvms=list virtualmachines")

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
        result.exit_code == 2


class TestLogin(object):

    def test_no_profile(self, runner, cli):
        result = runner.invoke(cli, ['--profile', 'profile1', 'login'])
        assert result.exit_code == 2
        assert result.exception
        assert "Profile 'profile1' does not exists." in result.output

    def test_no_credentials(self, runner, cli, default_config):
        with mock.patch('slipstream.cli.api.Api.verify', side_effect=[False, True]):
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
        parser.read(default_config.strpath)
        assert parser.get('slipstream', 'username') == 'clara'
        assert parser.get('slipstream', 'password') == 's3cr3t'

    def test_with_credentials(self, runner, cli, default_config):
        with mock.patch('slipstream.cli.api.Api.verify', return_value=True):
            result = runner.invoke(cli, ['login'], input=("alice\nh4x0r\n"))

        assert result.exit_code == 0
        assert result.output == ("Enter your SlipStream credentials.\n"
                                 "Username: alice\n"
                                 "Password (typing will be hidden): \n"
                                 "Authentication successful.\n")

        parser = configparser.RawConfigParser()
        parser.read(default_config.strpath)
        assert parser.get('slipstream', 'username') == 'alice'
        assert parser.get('slipstream', 'password') == 'h4x0r'

    def test_with_config_and_profile(self, runner, cli, tmpdir):
        config = tmpdir.join('slipstreamconfig')
        config.write("[profile1]\nendpoint = https://example.com")

        with mock.patch('slipstream.cli.api.Api.verify', return_value=True):
            result = runner.invoke(cli, ['-p', 'profile1', '-c', config.strpath,
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
        assert parser.get('profile1', 'password') == 'staple horse'
        assert parser.has_section('slipstream') is False


class TestLogout(object):

    def test_no_credentials(self, runner, cli):
        result = runner.invoke(cli, ['logout'])
        assert result.exit_code == 0
        assert result.output == "Local credentials cleared.\n"

    def test_with_credentials(self, runner, cli, default_config):
        default_config.write("[slipstream]\n"
                             "username = clara\n"
                             "password=s3cr3t\n")

        result = runner.invoke(cli, ['logout'])
        assert result.exit_code == 0
        assert result.output == "Local credentials cleared.\n"

        parser = configparser.RawConfigParser()
        parser.read(default_config.strpath)
        with pytest.raises(configparser.NoOptionError):
            parser.get('slipstream', 'username')
            parser.get('slipstream', 'password')


@pytest.mark.usefixtures('authenticated')
class TestListApplications(object):

    def test_list_all(self, runner, cli, apps):
        with mock.patch('slipstream.cli.api.Api.list_applications',
                        return_value=iter(apps)):
            result = runner.invoke(cli, ['list', 'applications'])
            assert result.exit_code == 0
            assert 'wordpress' in result.output
            assert 'ubuntu-12.04' in result.output


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
