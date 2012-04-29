from functools import wraps
from fabric.decorators import _wrap_as_new
from fabric.api import settings

from .conf import awsfab_settings
from .ec2 import Ec2InstanceWrapper


def ec2instance(nametag=None, instanceid=None):
    """
    Wraps the decorated function just as if it had been decorated with::

        @fabric.settings(key_filename='<ec2 instance key list>', host_string='ssh_user@public_dns')

    The settings are from ``awsfab_settings.EC2_INSTANCES[instancename]``.
    """
    instance = Ec2InstanceWrapper.get_by_nametag(nametag)
    ssh_uri = instance.get_ssh_uri()
    key_filenames = awsfab_settings.get_key_filenames(instance['key_name'])
    def outer(func):
        @wraps(func)
        def inner(*args, **kwargs):
            with settings(key_filename=key_filenames, host_string=ssh_uri):
                return func(*args, **kwargs)
        return _wrap_as_new(func, inner)
    return outer
