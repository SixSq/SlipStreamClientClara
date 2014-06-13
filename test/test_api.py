from __future__ import unicode_literals

import os
import uuid

import pytest
import responses
import requests


def load_fixture(filename):
    return open(
        os.path.join(os.path.dirname(__file__), 'fixtures', filename)
    ).read()


def test_verify(api):
    @responses.activate
    def run():
        responses.add(responses.GET, 'https://slipstream.sixsq.com/dashboard',
                      status=200)
        assert api.verify() is True

        responses.reset()
        responses.add(responses.GET, 'https://slipstream.sixsq.com/dashboard',
                      status=401)
        assert api.verify() is False

        responses.reset()
        responses.add(responses.GET, 'https://slipstream.sixsq.com/dashboard',
                      status=503)
        with pytest.raises(requests.HTTPError):
            api.verify()

    run()


def test_list_applications(api, apps):
    @responses.activate
    def run():
        responses.add(responses.GET, 'https://slipstream.sixsq.com/',
                      body=load_fixture('index.xml'), status=200,
                      content_type='application/xml')
        assert list(api.list_applications()) == apps

    run()


def test_list_virtualmachines(api, vms):
    @responses.activate
    def run():
        responses.add(responses.GET, 'https://slipstream.sixsq.com/vms',
                      body=load_fixture('vms.xml'), status=200,
                      content_type='application/xml')
        assert list(api.list_virtualmachines()) == vms

    run()


def test_list_runs(api, runs):
    @responses.activate
    def run():
        responses.add(responses.GET, 'https://slipstream.sixsq.com/run',
                      body=load_fixture('run.xml'), status=200,
                      content_type='application/xml')
        assert list(api.list_runs()) == runs

    run()


def test_terminate(api):
    @responses.activate
    def deleted():
        run_id = uuid.uuid4()
        responses.add(responses.DELETE,
                      'https://slipstream.sixsq.com/run/%s' % run_id,
                      status=204)
        assert api.terminate(run_id) is True

    @responses.activate
    def raises_error():
        run_id = uuid.uuid4()
        responses.add(responses.DELETE,
                      'https://slipstream.sixsq.com/run/%s' % run_id,
                      status=409)
        with pytest.raises(requests.HTTPError):
            api.terminate(run_id)

    deleted()
    raises_error()


def test_usage(api, usage):
    @responses.activate
    def run():
        responses.add(responses.GET, 'https://slipstream.sixsq.com/dashboard',
                      body=load_fixture('dashboard.xml'), status=200,
                      content_type='application/xml')
        assert list(api.usage()) == usage

    run()
