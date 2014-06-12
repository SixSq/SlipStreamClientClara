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

VirtualMachine = collections.namedtuple('VirtualMachines', [
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
