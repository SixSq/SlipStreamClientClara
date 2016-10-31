from __future__ import unicode_literals

import os
import uuid

import requests

import mock
import pytest
import responses

from slipstream.cli import models

requests.packages.urllib3.disable_warnings()

def load_fixture(filename):
    return open(
        os.path.join(os.path.dirname(__file__), 'fixtures', filename)
    ).read()


def test_login(api, cookie_file):
    username = 'clara'
    password = 's3cr3t'

    @responses.activate
    def run():
        responses.add(responses.POST, 'https://nuv.la/auth/login',
                      status=303)
        with mock.patch.object(api.session, 'cookies'):
            api.login(username, password)
            assert api.session.cookies.__getitem__.calls_with('com.sixsq.slipstream.cookie')
            assert api.session.cookies.save.called is True

        responses.reset()
        responses.add(responses.POST, 'https://nuv.la/auth/login',
                      status=401)
        with pytest.raises(requests.HTTPError):
            api.login(username, password)

        responses.reset()
        responses.add(responses.POST, 'https://nuv.la/auth/login',
                      status=503)
        with pytest.raises(requests.HTTPError):
            api.login(username, password)

    run()


def test_logout(api):
    @responses.activate
    def run():
        responses.add(responses.GET, 'https://nuv.la/logout',
                      status=303)
        with mock.patch.object(api, 'session'):
            api.logout()
            api.session.clear.assert_called_with('nuv.la')

    run()


def test_list_applications(api, apps):
    @responses.activate
    def run():
        responses.add(responses.GET, 'https://nuv.la/appstore',
                      body=load_fixture('appstore.xml'), status=200,
                      content_type='application/xml')
        assert list(api.list_applications()) == apps

    run()


def test_list_modules(api):
    @responses.activate
    def list_root():
        responses.add(responses.GET, 'https://nuv.la/module',
                      body=load_fixture('module.xml'), status=200,
                      content_type='application/xml')
        modules = list(api.list_modules())
        assert len(modules) == 1
        assert modules[0].name == 'examples'

    @responses.activate
    def list_all():
        responses.add(responses.GET, 'https://nuv.la/module',
                      body=load_fixture('module.xml'), status=200,
                      content_type='application/xml')
        responses.add(responses.GET, 'https://nuv.la/module/examples/56',
                      body=load_fixture('examples.xml'), status=200,
                      content_type='application/xml')
        responses.add(responses.GET, 'https://nuv.la/module/examples/images/57',
                      body=load_fixture('images.xml'), status=200,
                      content_type='application/xml')
        responses.add(responses.GET, 'https://nuv.la/module/examples/tutorials/58',
                      body=load_fixture('tutorials.xml'), status=200,
                      content_type='application/xml')
        responses.add(responses.GET, 'https://nuv.la/module/examples/tutorials/service-testing/60',
                      body=load_fixture('service_testing.xml'), status=200,
                      content_type='application/xml')
        modules = list(api.list_modules(recurse=True))
        assert len(modules) == 9
        assert modules[0].name == 'examples'
        assert modules[1].name == 'images'
        assert modules[2].name == 'centos-6'
        assert modules[3].name == 'ubuntu-12.04'
        assert modules[4].name == 'tutorials'
        assert modules[5].name == 'service-testing'
        assert modules[6].name == 'apache'
        assert modules[7].name == 'client'
        assert modules[8].name == 'system'

    @responses.activate
    def list_path():
        responses.add(responses.GET, 'https://nuv.la/module/examples',
                      body=load_fixture('examples.xml'), status=200,
                      content_type='application/xml')
        modules = list(api.list_modules(path='examples'))
        assert len(modules) == 2
        assert modules[0].name == 'images'
        assert modules[1].name == 'tutorials'

    @responses.activate
    def list_path_recursive():
        responses.add(responses.GET, 'https://nuv.la/module/examples/56',
                      body=load_fixture('examples.xml'), status=200,
                      content_type='application/xml')
        responses.add(responses.GET, 'https://nuv.la/module/examples/images/57',
                      body=load_fixture('images.xml'), status=200,
                      content_type='application/xml')
        responses.add(responses.GET, 'https://nuv.la/module/examples/tutorials/58',
                      body=load_fixture('tutorials.xml'), status=200,
                      content_type='application/xml')
        responses.add(responses.GET, 'https://nuv.la/module/examples/tutorials/service-testing/60',
                      body=load_fixture('service_testing.xml'), status=200,
                      content_type='application/xml')
        modules = list(api.list_modules(path='examples/56', recurse=True))
        assert len(modules) == 8
        assert modules[0].name == 'images'
        assert modules[1].name == 'centos-6'
        assert modules[2].name == 'ubuntu-12.04'
        assert modules[3].name == 'tutorials'
        assert modules[4].name == 'service-testing'
        assert modules[5].name == 'apache'
        assert modules[6].name == 'client'
        assert modules[7].name == 'system'


    list_root()
    list_all()
    list_path()
    list_path_recursive()


def test_list_virtualmachines(api, vms):
    @responses.activate
    def run():
        responses.add(responses.GET, 'https://nuv.la/vms',
                      body=load_fixture('vms.xml'), status=200,
                      content_type='application/xml')
        assert list(api.list_virtualmachines()) == vms

    run()


def test_list_runs(api, runs):
    @responses.activate
    def run():
        responses.add(responses.GET, 'https://nuv.la/run',
                      body=load_fixture('run.xml'), status=200,
                      content_type='application/xml')
        assert list(api.list_runs()) == runs

    run()


def test_build_image(api):
    @responses.activate
    def default():
        url = 'https://nuv.la/run'
        run_id = uuid.uuid4()
        responses.add(responses.POST, url, status=201,
                      adding_headers={'location': '%s/%s' % (url, run_id)})
        assert api.build_image('clara/ubuntu-14.04') == run_id
        call = responses.calls[0]
        assert 'parameter--cloudservice=default' in call.request.body
        assert 'type=Machine' in call.request.body
        assert 'refqname=clara%2Fubuntu-14.04' in call.request.body

    @responses.activate
    def defined_cloud():
        url = 'https://nuv.la/run'
        run_id = uuid.uuid4()
        responses.add(responses.POST, url, status=201,
                      adding_headers={'location': '%s/%s' % (url, run_id)})

        assert api.build_image('clara/ubuntu-14.04', cloud='cloud1') == run_id

        call = responses.calls[0]
        assert 'parameter--cloudservice=cloud1' in call.request.body
        assert 'type=Machine' in call.request.body
        assert 'refqname=clara%2Fubuntu-14.04' in call.request.body

    default()
    defined_cloud()


def test_run_image(api):
    @responses.activate
    def default():
        url = 'https://nuv.la/run'
        run_id = uuid.uuid4()
        responses.add(responses.POST, url, status=201,
                      adding_headers={'location': '%s/%s' % (url, run_id)})
        assert api.deploy()'clara/centos-6', {'refqname': path}) == run_id
        call = responses.calls[0]
        assert 'parameter--cloudservice=default' in call.request.body
        assert 'type=Run' in call.request.body
        assert 'refqname=clara%2Fcentos-6' in call.request.body

    @responses.activate
    def defined_cloud():
        url = 'https://nuv.la/run'
        run_id = uuid.uuid4()
        responses.add(responses.POST, url, status=201,
                      adding_headers={'location': '%s/%s' % (url, run_id)})

        assert api.run('clara/centos-6', cloud='cloud1') == run_id

        call = responses.calls[0]
        assert 'parameter--cloudservice=cloud1' in call.request.body
        assert 'type=Run' in call.request.body
        assert 'refqname=clara%2Fcentos-6' in call.request.body

    default()
    defined_cloud()


def test_run_deployment(api):
    @responses.activate
    def default():
        url = 'https://nuv.la/run'
        run_id = uuid.uuid4()
        responses.add(responses.POST, url, status=201,
                      adding_headers={'location': '%s/%s' % (url, run_id)})
        assert api.run_deployment('clara/wordpress') == run_id
        call = responses.calls[0]
        assert call.request.body == 'refqname=clara%2Fwordpress'

    @responses.activate
    def with_params():
        url = 'https://nuv.la/run'
        run_id = uuid.uuid4()
        responses.add(responses.POST, url, status=201,
                      adding_headers={'location': '%s/%s' % (url, run_id)})

        assert api.run_deployment(
            path='clara/wordpress',
            params=(
                ('wp', ('cloudservice', 'cloud1')),
                ('wp', ('multiplicity', 2))
            )) == run_id

        call = responses.calls[0]
        assert 'parameter--node--wp--multiplicity=2' in call.request.body
        assert 'parameter--node--wp--cloudservice=cloud1' in call.request.body
        assert 'refqname=clara%2Fwordpress' in call.request.body

    default()
    with_params()


def test_terminate(api):
    @responses.activate
    def deleted():
        run_id = uuid.uuid4()
        responses.add(responses.DELETE,
                      'https://nuv.la/run/%s' % run_id,
                      status=204)
        assert api.terminate(run_id) is True

    @responses.activate
    def raises_error():
        run_id = uuid.uuid4()
        responses.add(responses.DELETE,
                      'https://nuv.la/run/%s' % run_id,
                      status=409)
        with pytest.raises(requests.HTTPError):
            api.terminate(run_id)

    deleted()
    raises_error()


def test_usage(api, usage):
    @responses.activate
    def run():
        responses.add(responses.GET, 'https://nuv.la/dashboard',
                      body=load_fixture('dashboard.xml'), status=200,
                      content_type='application/xml')
        assert list(api.usage()) == usage

    run()


def test_get_module(api):
    app = models.Module(name='centos-6',
                        type='component',
                        version=479,
                        path='examples/images/centos-6',
                        created='2013-12-09 11:14:44.749 UTC',
                        modified='2014-06-24 10:22:23.371 UTC',
                        description='Minimal installation of the CentOS 6 operating system.')

    @responses.activate
    def run():
        responses.add(responses.GET, 'https://nuv.la/module/examples/images/centos-6',
                      body=load_fixture('centos-6.xml'), status=200,
                      content_type='application/xml')
        assert api.get_module('examples/images/centos-6') == app

        responses.reset()
        responses.add(responses.GET, 'https://nuv.la/module/examples/images/centos-6/479',
                      body=load_fixture('centos-6.xml'), status=200,
                      content_type='application/xml')
        assert api.get_module('examples/images/centos-6/479') == app

        responses.reset()
        responses.add(responses.GET, 'https://nuv.la/module/examples/images/centos-6',
                      body=load_fixture('centos-6.xml'), status=200,
                      content_type='application/xml')
        assert api.get_module('module/examples/images/centos-6') == app

        responses.reset()
        responses.add(responses.GET, 'https://nuv.la/module/foo',
                      status=404, content_type='application/xml')
        with pytest.raises(requests.HTTPError):
            api.get_module('foo')

    run()


def test_publish(api):
    @responses.activate
    def run():
        responses.add(responses.PUT, 'https://nuv.la/module/examples/images/centos-6/publish',
                      status=204, content_type='application/xml')
        assert api.publish('examples/images/centos-6') is True

        responses.reset()
        responses.add(responses.PUT, 'https://nuv.la/module/examples/images/centos-6/publish',
                      status=409, content_type='application/xml')
        with pytest.raises(requests.HTTPError):
            api.publish('examples/images/centos-6')

    run()


def test_unpublish(api):
    @responses.activate
    def run():
        responses.add(responses.DELETE, 'https://nuv.la/module/examples/images/centos-6/publish',
                      status=204, content_type='application/xml')
        assert api.unpublish('examples/images/centos-6') is True

    run()


def test_delete_module(api):
    @responses.activate
    def run():
        responses.add(responses.DELETE, 'https://nuv.la/module/examples/images/centos-6',
                      status=204, content_type='application/xml')
        assert api.delete_module('examples/images/centos-6') is True

    run()
