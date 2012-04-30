from functools import wraps
from fabric.decorators import _wrap_as_new
from fabric.api import settings, abort

from .ec2.api import Ec2InstanceWrapper


def ec2instance(nametag=None, instanceid=None):
    """
    Wraps the decorated function to execute as if it had been invoked with
    ``--ec2names`` or ``--ec2ids``.
    """
    def outer(func):
        @wraps(func)
        def inner(*args, **kwargs):
            if instanceid:
                instancewrapper = Ec2InstanceWrapper.get_by_instanceid(instanceid)
            elif nametag:
                instancewrapper = Ec2InstanceWrapper.get_by_nametag(nametag)
            else:
                raise ValueError('nametag or instanceid must be supplied.')

            state_name = instancewrapper['state']
            if not state_name == 'running':
                prettyname = instancewrapper.prettyname()
                abort('Instance, {prettyname}, is not running. (Current state={state_name})'.format(**vars()))
            ssh_uri = instancewrapper.get_ssh_uri()
            key_filename = instancewrapper.get_ssh_key_filename()

            with settings(key_filename=key_filename, host_string=ssh_uri):
                return func(*args, **kwargs)
        return _wrap_as_new(func, inner)
    return outer
