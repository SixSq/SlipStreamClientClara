from __future__ import unicode_literals

import collections

App = collections.namedtuple('App', [
    'name',
    'type',
    'version',
    'path',
])

Run = collections.namedtuple('Run', [
    'id',
    'module',
    'status',
    'started_at',
    'cloud',
])

VirtualMachine = collections.namedtuple('VirtualMachine', [
    'id',
    'cloud',
    'status',
    'run_id',
])

Usage = collections.namedtuple('Usage', [
    'cloud',
    'usage',
    'quota',
])
