# following PEP 386
__version__ = "0.4.0"


def main():
    from .commands import cli
    cli(auto_envvar_prefix='SLIPSTREAM')

if __name__ == '__main__':
    main()
