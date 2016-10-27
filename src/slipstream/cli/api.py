from __future__ import absolute_import

import os
import stat
import uuid

import requests
from six.moves.urllib.parse import urlparse
from six.moves.http_cookiejar import MozillaCookieJar

from . import conf, models
from .log import logger

try:
    from defusedxml import cElementTree as etree
except ImportError:
    from defusedxml import ElementTree as etree


def mod_url(path):
    parts = path.strip('/').split('/')
    if parts[0] == 'module':
        del parts[0]
    return '/module/' + '/'.join(parts)


def mod(path, with_version=True):
    parts = path.split('/')
    if with_version:
        return '/'.join(parts[1:])
    else:
        return '/'.join(parts[1:-1])

def get_module_type(category):
    mapping = {'image': 'component',
               'deployment': 'application'}
    return mapping.get(category.lower(), category.lower())

def ElementTree__iter(root):
    return getattr(root, 'iter',  # Python 2.7 and above
                   root.getiterator)  # Python 2.6 compatibility


class SessionStore(requests.Session):
    """A ``requests.Session`` subclass implementing a file-based session store.
    """

    def __init__(self, cookie_file=None):
        super(SessionStore, self).__init__()
        if cookie_file is None:
            cookie_file = conf.DEFAULT_COOKIE_FILE
        cookie_dir = os.path.dirname(cookie_file)
        self.cookies = MozillaCookieJar(cookie_file)
        # Create the $HOME/.slipstream dir if it doesn't exist
        if not os.path.isdir(cookie_dir):
            os.mkdir(cookie_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        # Load existing cookies if the cookies.txt exists
        if os.path.isfile(cookie_file):
            self.cookies.load(ignore_discard=True)
            self.cookies.clear_expired_cookies()

    def request(self, *args, **kwargs):
        response = super(SessionStore, self).request(*args, **kwargs)
        self.cookies.save(ignore_discard=True)
        return response

    def clear(self, domain):
        """Clear cookies for the specified domain."""
        try:
            self.cookies.clear(domain)
            self.cookies.save()
        except KeyError:
            pass


class Api(object):

    def __init__(self, endpoint=None, cookie_file=None, insecure=False):
        self.endpoint = conf.DEFAULT_ENDPOINT if endpoint is None else endpoint
        self.session = SessionStore(cookie_file)
        self.session.verify = (insecure == False)
        self.session.headers.update({'Accept': 'application/xml'})
        if insecure:
            requests.packages.urllib3.disable_warnings(
                requests.packages.urllib3.exceptions.InsecureRequestWarning)

    def login(self, username, password):
        response = self.session.post('%s/auth/login' % self.endpoint, data={
            'username': username,
            'password': password
        })
        response.raise_for_status()

    def logout(self):
        response = self.session.get('%s/logout' % self.endpoint)
        response.raise_for_status()
        url = urlparse(self.endpoint)
        self.session.clear(url.netloc)

    def xml_get(self, url, **params):
        response = self.session.get('%s%s' % (self.endpoint, url),
                                    headers={'Accept': 'application/xml'},
                                    params=params)
        response.raise_for_status()
        return etree.fromstring(response.text)

    def json_get(self, url, **params):
        response = self.session.get('%s%s' % (self.endpoint, url),
                                    headers={'Accept': 'application/json'},
                                    params=params)
        response.raise_for_status()
        return response.json()

    def list_applications(self):
        root = self.xml_get('/appstore')
        for elem in ElementTree__iter(root)('item'):
            yield models.App(name=elem.get('name'),
                             type=get_module_type(elem.get('category')),
                             version=int(elem.get('version')),
                             path=mod(elem.get('resourceUri'),
                                      with_version=False))

    def get_module(self, path):
        url = mod_url(path)
        try:
            root = self.xml_get(url)
        except requests.HTTPError as e:
            if e.response.status_code == 403:
                logger.debug("Access denied for path: {0}. Skipping.".format(path))
            raise

        module = models.Module(name=root.get('shortName'),
                               type=get_module_type(root.get('category')),
                               created=root.get('creation'),
                               modified=root.get('lastModified'),
                               description=root.get('description'),
                               version=int(root.get('version')),
                               path=mod('%s/%s' % (root.get('parentUri').strip('/'),
                                                   root.get('shortName'))))
        return module
        

    def list_modules(self, path=None, recurse=False):
        logger.log(logger.VERBOSE_DEBUG, "Starting with path: {0}".format(path))
        # Path normalization
        if not path:
            url = '/module'
        else:
            url = mod_url(path)
        logger.log(logger.VERBOSE_DEBUG, "Using normalized URL: {0}".format(url))

        try:
            root = self.xml_get(url)
        except requests.HTTPError as e:
            if e.response.status_code == 403:
                logger.debug("Access denied for path: {0}. Skipping.".format(path))
                return
            raise

        for elem in ElementTree__iter(root)('item'):
            # Compute module path
            if elem.get('resourceUri'):
                app_path = elem.get('resourceUri')
            else:
                app_path = "%s/%s" % (root.get('parentUri').strip('/'),
                                      '/'.join([root.get('shortName'),
                                                elem.get('name'),
                                                elem.get('version')]))

            logger.debug("Found module with path: {0}".format(app_path))
            app = models.App(name=elem.get('name'),
                             type=get_module_type(elem.get('category')),
                             version=int(elem.get('version')),
                             path=mod(app_path, with_version=False))
            yield app
            if app.type == 'project' and recurse:
                logger.debug("Recursing into path: {0}".format(app_path))
                for app in self.list_modules(app_path, recurse):
                    yield app

    def list_runs(self, inactive=False):
        root = self.xml_get('/run', activeOnly=(not inactive))
        for elem in ElementTree__iter(root)('item'):
            yield models.Run(id=uuid.UUID(elem.get('uuid')),
                             module=mod(elem.get('moduleResourceUri')),
                             status=elem.get('status').lower(),
                             started_at=elem.get('startTime'),
                             cloud=elem.get('cloudServiceNames'))

    def list_virtualmachines(self):
        root = self.xml_get('/vms')
        for elem in ElementTree__iter(root)('vm'):
            run_id_str = elem.get('runUuid')
            run_id = uuid.UUID(run_id_str) if run_id_str is not None else None
            yield models.VirtualMachine(id=elem.get('instanceId'),
                                        cloud=elem.get('cloud'),
                                        status=elem.get('state').lower(),
                                        run_id=run_id)

    def build_image(self, path, cloud=None):
        response = self.session.post(self.endpoint + '/run', data={
            'type': 'Machine',
            'refqname': path,
            'parameter--cloudservice': cloud or 'default',
        })
        response.raise_for_status()
        run_id = response.headers['location'].split('/')[-1]
        return uuid.UUID(run_id)

    def run(self, params={}):
        response = self.session.post(self.endpoint + '/run', data=params)
        response.raise_for_status()
        run_id = response.headers['location'].split('/')[-1]
        return uuid.UUID(run_id)

    def terminate(self, run_id):
        response = self.session.delete('%s/run/%s' % (self.endpoint, run_id))
        response.raise_for_status()
        return True

    def usage(self):
        root = self.xml_get('/dashboard')
        for elem in ElementTree__iter(root)('cloudUsage'):
            yield models.Usage(cloud=elem.get('cloud'),
                               quota=int(elem.get('vmQuota')),
                               run_usage=int(elem.get('userRunUsage')),
                               vm_usage=int(elem.get('userVmUsage')),
                               inactive_vm_usage=int(elem.get('userInactiveVmUsage')),
                               others_vm_usage=int(elem.get('othersVmUsage')),
                               pending_vm_usage=int(elem.get('pendingVmUsage')),
                               unknown_vm_usage=int(elem.get('unknownVmUsage')))

    #def get_module(self, path):
    #    root = self.xml_get(mod_url(path))
    #    return models.App(name=root.get('shortName'),
    #                      type=root.get('category').lower(),
    #                      version=int(root.get('version')),
    #                      path=mod('%s/%s' % (root.get('parentUri').strip('/'),
    #                                          root.get('shortName'))))

    def publish(self, path):
        response = self.session.put('%s%s/publish' % (self.endpoint,
                                                      mod_url(path)))
        response.raise_for_status()
        return True

    def unpublish(self, path):
        response = self.session.delete('%s%s/publish' % (self.endpoint,
                                                         mod_url(path)))
        response.raise_for_status()
        return True

    def delete_module(self, path):
        response = self.session.delete('%s%s' % (self.endpoint, mod_url(path)))

        response.raise_for_status()
        return True
