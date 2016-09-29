import os

DEFAULT_PROFILE = 'nuvla'
DEFAULT_ENDPOINT = 'https://nuv.la'
COOKIE_FILE_PATH = '~/.slipstream/'
COOKIE_FILE_NAME_FORMAT = 'cookies-{profile}.txt'
DEFAULT_CONFIG_FILE = os.path.expanduser('~/.slipstream/config')
DEFAULT_COOKIE_FILE = os.path.expanduser(COOKIE_FILE_PATH + COOKIE_FILE_NAME_FORMAT.format(profile=DEFAULT_PROFILE))
