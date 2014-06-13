import click

from six.moves.urllib.parse import urlparse


class URL(click.ParamType):
    name = 'url'

    def convert(self, value, param, ctx):
        if not isinstance(value, tuple):
            url = urlparse.urlparse(value)
            if url.scheme not in ('http', 'https'):
                self.fail('invalid URL scheme (%s).  Only HTTP(S) URLs are '
                          'allowed' % value.scheme, param, ctx)
        return value


class KeyValue(click.ParamType):
    name = 'keyvalue'

    def convert(self, value, param, ctx):
        return tuple(value.split('='))
