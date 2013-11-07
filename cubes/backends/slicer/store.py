# -*- coding=utf -*-
from ...model import *
from ...browser import *
from ...stores import Store
from ...providers import ModelProvider
from ...errors import *
from ...common import get_logger
import json
import urllib2
import urllib

DEFAULT_SLICER_URL = "http://localhost:5000"

class SlicerStore(Store):
    def __init__(self, url=None, authentication=None,
                 auth_identity=None, auth_parameter=None,
                 **options):

        url = url or DEFAULT_SLICER_URL

        self.url = url
        self.logger = get_logger()

        if authentication and authentication not in ["pass_parameter", "none"]:
            raise ConfigurationError("Unsupported authentication method '%s'"
                                     % authentication)

        self.authentication = authentication
        self.auth_identity = auth_identity
        self.auth_parameter = auth_parameter or "api_key"

        # TODO: cube prefix
        # TODO: model mappings as in mixpanel

    def request(self, action, params=None, is_lines=False):
        """
        * `action` – server action (path)
        # `params` – request parameters
        """

        params = dict(params) if params else {}

        if self.authentication == "pass_parameter":
            params[self.auth_parameter] = self.auth_identity

        params_str = urllib.urlencode(params)
        request_url = '%s/%s' % (self.url, action)

        if params_str:
            request_url += '?' + params_str

        self.logger.debug("slicer request: %s" % (request_url, ))
        response = urllib.urlopen(request_url)

        if response.getcode() == 404:
            raise MissingObjectError
        elif response.getcode() != 200:
            raise BackendError("Slicer request error (%s): %s"
                               % (response.getcode(), response.read()))

        if is_lines:
            return _JSONLinesIterator(response)
        else:
            try:
                result = json.loads(response.read())
            except:
                result = {}

            return result

    def cube_request(self, action, cube, params=None, is_lines=False):
        action = "cube/%s/%s" % (cube, action)
        return self.request(action, params, is_lines)


class _JSONLinesIterator(object):
    def __init__(self, stream):
        self.stream = stream

    def __iter__(self):
        for line in self.stream:
            yield json.loads(line)


class SlicerModelProvider(ModelProvider):

    def requires_store(self):
        return True

    def list_cubes(self):
        return self.store.request('cubes')

    def cube(self, name):
        try:
            cube_desc = self.store.cube_request("model", name)
        except MissingObjectError:
            raise NoSuchCubeError("Unknown cube '%s'" % name, name)

        # create_cube() expects dimensions to be a list of names and linked
        # later, the Slicer returns whole dimension descriptions

        dimensions = cube_desc.pop("dimensions")

        cube_desc['datastore'] = self.store_name
        cube = create_cube(cube_desc)
        for dim in dimensions:
            dim = create_dimension(dim)
            cube.add_dimension(dim)

        return cube

    def dimension(self, name):
        raise NoSuchDimensionError(name)
