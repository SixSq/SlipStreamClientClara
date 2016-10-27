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


class NodeKeyValue(click.ParamType):
    name = 'nodekeyvalue'

    @staticmethod
    def get_key_val(key_val):
        temp = key_val.split('=', 1)
        if len(temp) == 1:
            k = ''
            v = temp[0]
        else:
            k = temp[0]
            v = temp[1]
        return k, v

    def convert(self, value, param, ctx):
        try:
            temp = value.split(':', 1)
            n = 'default'
            if len(temp) == 1:  # value or key=value
                k, v = NodeKeyValue.get_key_val(temp[0])
            else:  # node:value or node:key=value
                n = temp[0]
                k, v = NodeKeyValue.get_key_val(temp[1])

            if param.name == 'cloud':
                if k != '':
                    raise ValueError
                k = 'cloudservice'

            if n == 'default':
                if param.name == 'param':
                    if k == '':
                        raise ValueError
                    return 'parameter--{0}'.format(k), v
                elif param.name == 'cloud':
                    return 'parameter--cloudservice', v
            else:
                if k == '':
                    raise ValueError
                return 'parameter--node--{0}--{1}'.format(n, k), v
        except ValueError:
            self.fail("%s is not a valid!\nAuthorized format: %s" % (value, param.metavar), param, ctx)
