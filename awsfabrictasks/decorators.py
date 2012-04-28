from functools import wraps
from fabric.decorators import _wrap_as_new
from fabric.api import settings

from .conf import awsfab_settings
from .ec2 import get_ec2instance_uri, get_ec2instanceconf


def ec2instance(instancename):
    """
    Wraps the decorated function just as if it had been decorated with::

        @fabric.settings(key_filename='<ec2 instance key list>', host_string='ssh_user@public_dns')

    The settings are from ``awsfab_settings.EC2_INSTANCES[instancename]``.
    """
    conf = get_ec2instanceconf(instancename)
    key_name = conf['key_name']
    key_filenames = awsfab_settings.get_key_filenames(key_name)
    ssh_uri = get_ec2instance_uri(conf)
    def outer(func):
        @wraps(func)
        def inner(*args, **kwargs):
            with settings(key_filename=key_filenames, host_string=ssh_uri):
                return func(*args, **kwargs)
        return _wrap_as_new(func, inner)
    return outer
