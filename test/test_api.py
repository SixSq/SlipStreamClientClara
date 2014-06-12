import os

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
        with pytest.raises(requests.RequestException):
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
