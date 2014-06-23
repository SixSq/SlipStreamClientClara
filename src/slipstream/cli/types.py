import click

from six.moves.urllib.parse import urlparse


class URL(click.ParamType):
    name = 'url'

    def convert(self, value, param, ctx):
        if not isinstance(value, tuple):
            url = urlparse(value)
            if url.scheme not in ('http', 'https'):
                self.fail('invalid URL scheme (%s).  Only HTTP(S) URLs are '
                          'allowed' % url.scheme, param, ctx)
        return value


class KeyValue(click.ParamType):
    name = 'keyvalue'

    def convert(self, value, param, ctx):
        try:
            return tuple(value.split('='))
        except ValueError:
            self.fail("%s is not a valid KEY=VALUE value" % value, param, ctx)


class NodeKeyValue(click.ParamType):
    name = 'nodekeyvalue'

    def convert(self, value, param, ctx):
        try:
            node, param = value.split(':', 1)
            return (node, tuple(param.split('=', 1)))
        except ValueError:
            self.fail("%s is not a valid NODE:KEY=VALUE value" % value, param, ctx)

