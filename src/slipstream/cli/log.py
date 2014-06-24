import logging

import click
from click._compat import get_text_stderr


class Logger(object):
    """
    Logging object for use in command-line script. Allows ranges of
    levels, to avoid some redundancy of displayed information.
    """
    VERBOSE_DEBUG = logging.DEBUG - 1
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    NOTIFY = (logging.INFO + logging.WARNING) / 2
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    FATAL = logging.FATAL

    LEVELS = [VERBOSE_DEBUG, DEBUG, INFO, NOTIFY, WARNING, ERROR, FATAL]
    COLORS = {
        VERBOSE_DEBUG: 'green',
        DEBUG: 'green',
        WARNING: 'yellow',
        ERROR: 'red',
        FATAL: 'red',
    }

    def __init__(self):
        self.level = self.NOTIFY

    def debug(self, msg, *args, **kwargs):
        self.log(self.DEBUG, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.log(self.INFO, msg, *args, **kwargs)

    def notify(self, msg, *args, **kwargs):
        self.log(self.NOTIFY, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.log(self.WARNING, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.log(self.ERROR, msg, *args, **kwargs)

    def fatal(self, msg, *args, **kwargs):
        self.log(self.FATAL, msg, *args, **kwargs)

    def log(self, level, msg, *args, **kwargs):
        if args:
            if kwargs:
                raise TypeError(
                    "You may give positional or keyword arguments, not both")
        args = args or kwargs

        # render
        if args:
            rendered = msg % args
        else:
            rendered = msg

        # output
        if level >= self.level:
            color = self.COLORS.get(level)
            stream = get_text_stderr() if level >= self.WARNING else None
            click.secho(rendered, file=stream, fg=color)

    def set_level(self, level):
        if level < 0:
            self.level = self.LEVELS[0]
        elif level >= len(self.LEVELS):
            self.level = self.LEVELS[-1]
        else:
            self.level = self.LEVELS[level]

logger = Logger()
