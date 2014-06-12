from __future__ import absolute_import

import uuid

import requests

from . import models

try:
    from defusedxml import cElementTree as etree
except ImportError:
    from defusedxml import ElementTree as etree

DEFAULT_ENDPOINT = 'https://slipstream.sixsq.com'


def mod(path):
    return path.replace('module/', '')


def ElementTree__iter(root):
    return getattr(root, 'iter',      # Python 2.7 and above
                   root.getiterator)  # Python 2.6 compatibility


class Api(object):

    def __init__(self, username=None, password=None, endpoint=None):
        self.endpoint = DEFAULT_ENDPOINT if endpoint is None else endpoint
        self.session = requests.Session()
        self.session.auth = (username, password)

    def verify(self):
        response = self.session.get('%s/dashboard' % self.endpoint)
        if response.status_code == requests.codes.ok:
            return True
        if response.status_code == 401:
            return False
        response.raise_for_status()

    def xml_get(self, url):
        response = self.session.get('%s%s' % (self.endpoint, url),
                                    headers={'content-type': 'application/xml'})
        response.raise_for_status()
        return etree.fromstring(response.text)

    def json_get(self, url):
        response = self.session.get('%s%s' % (self.endpoint, url),
                                    headers={'content-type': 'application/json'})
        response.raise_for_status()
        return response.json()

    def list_applications(self):
        root = self.xml_get('/')
        for elem in ElementTree__iter(root)('item'):
            if elem.get('published', False):
                yield models.App(elem.get('name'),
                                 elem.get('category').lower(),
                                 int(elem.get('version')),
                                 mod(elem.get('resourceUri')))

    def list_runs(self):
        root = self.xml_get('/run')
        for elem in ElementTree__iter(root)('item'):
            if elem.get('type') == 'Run':
                yield models.Run(elem.get('uuid'),
                                 mod(elem.get('moduleResourceUri')),
                                 elem.get('status').lower(),
                                 elem.get('startTime'),
                                 elem.get('cloudServiceName'))

    def list_virtualmachines(self):
        root = self.xml_get('/vms')
        for elem in ElementTree__iter(root)('vm'):
            yield models.VirtualMachine(uuid.UUID(elem.get('instanceId')),
                                        elem.get('cloud'),
                                        elem.get('state').lower(),
                                        uuid.UUID(elem.get('runUuid')))

    def run_image(self, path, cloud='default'):
        response = self.session.post(self.endpoint + '/run', data={
            'type': 'Run',
            'refqname': path,
            'parameter--cloudservice': cloud,
        })
        response.raise_for_status()
        return response.headers['location'].split('/')[-1]

    def terminate(self, run_id):
        response = self.session.delete('%s/run/%s' % (self.endpoint, run_id))
        response.raise_for_status()

    def usage(self):
        root = self.xml_get('/dashboard')
        for elem in ElementTree__iter(root)('usageElement'):
            yield models.Usage(elem.get('cloud'), elem.get('currentUsage'),
                               elem.get('quota'))
