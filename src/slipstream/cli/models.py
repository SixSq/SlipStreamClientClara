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
    'run_usage',
    'vm_usage',
    'inactive_vm_usage',
    'others_vm_usage',
    'pending_vm_usage',
    'unknown_vm_usage',
    'quota',
])

Module = collections.namedtuple('Module', [
    'name',
    'type',
    'created',
    'modified',
    'description',
    'version',
    'path',
])

