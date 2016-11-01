from __future__ import absolute_import

import os
import stat
import uuid

import requests
from six import string_types, integer_types
from six.moves.urllib.parse import urlparse
from six.moves.http_cookiejar import MozillaCookieJar

from . import conf, models
from .log import logger

try:
    from defusedxml import cElementTree as etree
except ImportError:
    from defusedxml import ElementTree as etree


def _mod_url(path):
    parts = path.strip('/').split('/')
    if parts[0] == 'module':
        del parts[0]
    return '/module/' + '/'.join(parts)


def _mod(path, with_version=True):
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


class SlipStreamError(Exception):

    def __init__(self, reason):
        super(SlipStreamError, self).__init__(reason)
        self.reason = reason


class SessionStore(requests.Session):
    """A ``requests.Session`` subclass implementing a file-based session store."""

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
    """ This class is a Python wrapper&helper of the native SlipStream REST API"""

    GLOBAL_PARAMETERS = ['bypass-ssh-check', 'refqname', 'keep-running', 'tags', 'mutable', 'type']
    KEEP_RUNNING_VALUES = ['always', 'never', 'on-success', 'on-error']

    def __init__(self, endpoint=None, cookie_file=None, insecure=False):
        self.endpoint = conf.DEFAULT_ENDPOINT if endpoint is None else endpoint
        self.session = SessionStore(cookie_file)
        self.session.verify = (insecure == False)
        self.session.headers.update({'Accept': 'application/xml'})
        if insecure:
            requests.packages.urllib3.disable_warnings(
                requests.packages.urllib3.exceptions.InsecureRequestWarning)

    def login(self, username, password):
        """

        :param username: 
        :param password: 

        """
        response = self.session.post('%s/auth/login' % self.endpoint, data={
            'username': username,
            'password': password
        })
        response.raise_for_status()

    def logout(self):
        """ """
        response = self.session.get('%s/logout' % self.endpoint)
        response.raise_for_status()
        url = urlparse(self.endpoint)
        self.session.clear(url.netloc)

    def xml_get(self, url, **params):
        """

        :param url: 
        :param **params: 

        """
        response = self.session.get('%s%s' % (self.endpoint, url),
                                    headers={'Accept': 'application/xml'},
                                    params=params)
        response.raise_for_status()
        return etree.fromstring(response.text)

    def json_get(self, url, **params):
        """

        :param url: 
        :param **params: 

        """
        response = self.session.get('%s%s' % (self.endpoint, url),
                                    headers={'Accept': 'application/json'},
                                    params=params)
        response.raise_for_status()
        return response.json()

    def list_applications(self):
        """ """
        root = self.xml_get('/appstore')
        for elem in ElementTree__iter(root)('item'):
            yield models.App(name=elem.get('name'),
                             type=get_module_type(elem.get('category')),
                             version=int(elem.get('version')),
                             path=_mod(elem.get('resourceUri'),
                                      with_version=False))

    def get_module(self, path):
        """

        :param path: 

        """
        url = _mod_url(path)
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
                               path=_mod('%s/%s' % (root.get('parentUri').strip('/'),
                                                   root.get('shortName'))))
        return module

    def list_modules(self, path=None, recurse=False):
        """

        :param path: (Default value = None)
        :param recurse: (Default value = False)

        """
        logger.log(logger.VERBOSE_DEBUG, "Starting with path: {0}".format(path))
        # Path normalization
        if not path:
            url = '/module'
        else:
            url = _mod_url(path)
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
                             path=_mod(app_path, with_version=False))
            yield app
            if app.type == 'project' and recurse:
                logger.debug("Recursing into path: {0}".format(app_path))
                for app in self.list_modules(app_path, recurse):
                    yield app

    def list_runs(self, inactive=False):
        """

        :param inactive: (Default value = False)

        """
        root = self.xml_get('/run', activeOnly=(not inactive))
        for elem in ElementTree__iter(root)('item'):
            yield models.Run(id=uuid.UUID(elem.get('uuid')),
                             module=_mod(elem.get('moduleResourceUri')),
                             status=elem.get('status').lower(),
                             started_at=elem.get('startTime'),
                             cloud=elem.get('cloudServiceNames'))

    def list_virtualmachines(self):
        """ """
        root = self.xml_get('/vms')
        for elem in ElementTree__iter(root)('vm'):
            run_id_str = elem.get('runUuid')
            run_id = uuid.UUID(run_id_str) if run_id_str is not None else None
            yield models.VirtualMachine(id=elem.get('instanceId'),
                                        cloud=elem.get('cloud'),
                                        status=elem.get('state').lower(),
                                        run_id=run_id)

    def build_image(self, path, cloud=None):
        """

        :param path: 
        :param cloud: (Default value = None)

        """
        response = self.session.post(self.endpoint + '/run', data={
            'type': 'Machine',
            'refqname': path,
            'parameter--cloudservice': cloud or 'default',
        })
        response.raise_for_status()
        run_id = response.headers['location'].split('/')[-1]
        return uuid.UUID(run_id)

    def deploy(self, path, cloud=None, parameters=None, tags=None, keep_running=None, scalable=False, multiplicity=None,
               tolerate_failures=None, check_ssh_key=False, raw_params=None):
        """
        Run a component or an application
        
        :param path: The path of the component/application to deploy
        :type path: str
        :param cloud: A string or a dict to specify on which Cloud(s) to deploy the component/application.
                      To deploy a component simply specify the Cloud name as a string.
                      To deploy a deployment specify a dict with the nodenames as keys and Cloud names as values.
                      If not specified the user default cloud will be used.
        :type cloud: str or dict
        :param parameters: A dict of parameters to redefine for this deployment.
                           To redefine a parameter of a node use "<nodename>" as keys and dict of parameters as values.
                           To redefine a parameter of a component or a global parameter use "<parametername>" as the key.
        :type parameters: dict
        :param tags: List of tags that can be used to identify or annotate a deployment
        :type tags: str or list
        :param keep_running: [Only apply to applications] Define when to terminate or not a deployment when it reach the
                             'Ready' state. Possibles values: 'always', 'never', 'on-success', 'on-error'.
                             If scalable is set to True, this value is ignored and it will behave as if it was set to 'always'.
                             If not specified the user default will be used.
        :type keep_running: 'always' or 'never' or 'on-success' or 'on-error'
        :param scalable: [Only apply to applications] True to start a scalable deployment. Default: False
        :type scalable: bool
        :param multiplicity: [Only apply to applications] A dict to specify how many instances to start per node.
                             Nodenames as keys and number of instances to start as values.
        :type multiplicity: bool
        :param tolerate_failures: [Only apply to applications] A dict to specify how many failures to tolerate per node.
                                  Nodenames as keys and number of failure to tolerate as values.
        :type tolerate_failures: dict
        :param check_ssh_key: Set it to True if you want the SlipStream server to check if you have a public ssh key
                              defined in your user profile. Useful if you want to ensure you will have access to VMs.
        :type check_ssh_key: bool
        :param raw_params: This allows you to pass parameters directly in the request to the SlipStream server.
                           Keys must be formatted in the format understood by the SlipStream server.
        :type raw_params: dict

        :return: The deployment UUID of the newly created deployment
        :rtype: uuid.UUID
        """

        _raw_params = dict() if raw_params is None else raw_params
        _raw_params.update(self._convert_parameters_to_raw_params(parameters))
        _raw_params.update(self._convert_clouds_to_raw_params(cloud))
        _raw_params.update(self._convert_multiplicity_to_raw_params(multiplicity))
        _raw_params.update(self._convert_tolerate_failures_to_raw_params(tolerate_failures))
        _raw_params['refqname'] = path

        if tags:
            _raw_params['tags'] = tags

        if keep_running:
            if keep_running not in self.KEEP_RUNNING_VALUES:
                raise ValueError('"keep_running" should be one of {}, not "{}"'.format(self.KEEP_RUNNING_VALUES,
                                                                                     keep_running))
            _raw_params['keep-running'] = keep_running

        if scalable:
            _raw_params['mutable'] = 'on'

        if not check_ssh_key:
            _raw_params['bypass-ssh-check'] = 'true'

        response = self.session.post(self.endpoint + '/run', data=_raw_params)

        if response.status_code == 409:
            reason = etree.fromstring(response.text).get('detail')
            raise SlipStreamError(reason)

        response.raise_for_status()
        run_id = response.headers['location'].split('/')[-1]
        return uuid.UUID(run_id)

    def terminate(self, run_id):
        """

        :param run_id: 

        """
        response = self.session.delete('%s/run/%s' % (self.endpoint, run_id))
        response.raise_for_status()
        return True

    def usage(self):
        """ """
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

    def publish(self, path):
        """

        :param path: 

        """
        response = self.session.put('%s%s/publish' % (self.endpoint,
                                                      _mod_url(path)))
        response.raise_for_status()
        return True

    def unpublish(self, path):
        """

        :param path: 

        """
        response = self.session.delete('%s%s/publish' % (self.endpoint,
                                                         _mod_url(path)))
        response.raise_for_status()
        return True

    def delete_module(self, path):
        """

        :param path: 

        """
        response = self.session.delete('%s%s' % (self.endpoint, _mod_url(path)))

        response.raise_for_status()
        return True

    @staticmethod
    def _check_type(obj_name, obj, allowed_types):
        if not isinstance(obj, allowed_types):
            raise ValueError('Invalid type "{}" for "{}"'.format(type(obj), obj_name))

    @classmethod
    def _convert_clouds_to_raw_params(cls, clouds):
        return cls._convert_per_node_parameter_to_raw_params('cloudservice', clouds, allowed_types=string_types)

    @classmethod
    def _convert_multiplicity_to_raw_params(cls, multiplicity):
        return cls._convert_per_node_parameter_to_raw_params('multiplicity', multiplicity,
                                                             allowed_types=(integer_types, string_types))

    @classmethod
    def _convert_tolerate_failures_to_raw_params(cls, tolerate_failures):
        return cls._convert_per_node_parameter_to_raw_params('max-provisioning-failures', tolerate_failures,
                                                             allowed_types=(integer_types, string_types))

    @classmethod
    def _convert_per_node_parameter_to_raw_params(cls, parameter_name, parameters, allowed_types=(string_types, int),
                                                  allow_no_node=True):
        raw_params = dict()

        if parameters is None:
            return raw_params

        if isinstance(parameters, dict):
            for key, value in parameters.items():
                cls._check_type('{}:{}'.format(key, parameter_name), value, allowed_types)
                raw_params['parameter--node--{}--{}'.format(key, parameter_name)] = value
        elif allow_no_node:
            cls._check_type(parameter_name, parameters, allowed_types)
            raw_params['parameter--{}'.format(parameter_name)] = parameters
        else:
            cls._check_type(parameter_name, parameters, dict)

        return raw_params

    @classmethod
    def _convert_parameters_to_raw_params(cls, parameters):
        raw_params = dict()

        if parameters is None:
            return raw_params

        for key, value in parameters.items():
            if isinstance(value, dict):
                # Redefine node parameters
                for parameter_name, parameter_value in value.items():
                    raw_params['parameter--node--{}--{}'.format(key, parameter_name)] = parameter_value
            else:
                if key in cls.GLOBAL_PARAMETERS:
                    # Redefine a global parameter
                    raw_params[key] = value
                else:
                    # Redefine a component parameter
                    raw_params['parameter--{}'.format(key)] = value

        return raw_params



