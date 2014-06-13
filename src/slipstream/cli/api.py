from __future__ import absolute_import

import uuid

import requests

from . import models
from .conf import DEFAULT_ENDPOINT

try:
    from defusedxml import cElementTree as etree
except ImportError:
    from defusedxml import ElementTree as etree


def mod(path, with_version=True):
    parts = path.split('/')
    if with_version:
        return '/'.join(parts[1:])
    else:
        return '/'.join(parts[1:-1])


def ElementTree__iter(root):
    return getattr(root, 'iter',      # Python 2.7 and above
                   root.getiterator)  # Python 2.6 compatibility


class Api(object):

    def __init__(self, username=None, password=None, endpoint=None):
        self.endpoint = DEFAULT_ENDPOINT if endpoint is None else endpoint
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.verify = False

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
                yield models.App(name=elem.get('name'),
                                 type=elem.get('category').lower(),
                                 version=int(elem.get('version')),
                                 path=mod(elem.get('resourceUri'),
                                          with_version=False))

    def list_runs(self):
        root = self.xml_get('/run')
        for elem in ElementTree__iter(root)('item'):
            yield models.Run(id=uuid.UUID(elem.get('uuid')),
                             module=mod(elem.get('moduleResourceUri')),
                             status=elem.get('status').lower(),
                             started_at=elem.get('startTime'),
                             cloud=elem.get('cloudServiceName'))

    def list_virtualmachines(self):
        root = self.xml_get('/vms')
        for elem in ElementTree__iter(root)('vm'):
            yield models.VirtualMachine(id=uuid.UUID(elem.get('instanceId')),
                                        cloud=elem.get('cloud'),
                                        status=elem.get('state').lower(),
                                        run_id=uuid.UUID(elem.get('runUuid')))

    def run_image(self, path, cloud=None):
        response = self.session.post(self.endpoint + '/run', data={
            'type': 'Run',
            'refqname': path,
            'parameter--cloudservice': cloud or 'default',
        })
        response.raise_for_status()
        run_id = response.headers['location'].split('/')[-1]
        return uuid.UUID(run_id)

    def run_deployment(self, path, params=()):
        data = {'refqname': path}
        for node, (key, value) in params:
            data['parameter--node--{0}--{1}'.format(node, key)] = value

        response = self.session.post(self.endpoint + '/run', data=data)
        response.raise_for_status()
        run_id = response.headers['location'].split('/')[-1]
        return uuid.UUID(run_id)

    def terminate(self, run_id):
        response = self.session.delete('%s/run/%s' % (self.endpoint, run_id))
        response.raise_for_status()
        return True

    def usage(self):
        root = self.xml_get('/dashboard')
        for elem in ElementTree__iter(root)('usageElement'):
            yield models.Usage(cloud=elem.get('cloud'),
                               usage=int(elem.get('currentUsage')),
                               quota=int(elem.get('quota')))
