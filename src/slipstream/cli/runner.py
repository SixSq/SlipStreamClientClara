from __future__ import absolute_import

from .base import cli


def main():
    cli(auto_envvar_prefix='SLIPSTREAM')

if __name__ == '__main__':
    main()
