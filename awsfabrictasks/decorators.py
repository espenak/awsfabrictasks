from functools import wraps
from fabric.decorators import _wrap_as_new
from .ec2.api import Ec2InstanceWrapper


try:
    unicode = unicode
except NameError:
    basestring = (str, bytes)
    

def _list_annotating_decorator(attribute, *values):
    def attach_list(func):
        @wraps(func)
        def inner_decorator(*args, **kwargs):
            return func(*args, **kwargs)
        _values = values
        # Allow for single iterable argument as well as *args
        if len(_values) == 1 and not isinstance(_values[0], basestring):
            _values = _values[0]
        setattr(inner_decorator, attribute, list(_values))
        # Don't replace @task new-style task objects with inner_decorator by
        # itself -- wrap in a new Task object first.
        inner_decorator = _wrap_as_new(func, inner_decorator)
        return inner_decorator
    return attach_list


def ec2instance(nametag=None, instanceid=None, tags=None, region=None):
    """
    Wraps the decorated function to execute as if it had been invoked with
    ``--ec2names`` or ``--ec2ids``.
    """
    instancewrappers = []
    if instanceid:
        instancewrappers += [Ec2InstanceWrapper.get_by_instanceid(instanceid)]
    if nametag:
        instancewrappers += [Ec2InstanceWrapper.get_by_nametag(nametag)]
    if tags:
        instancewrappers += Ec2InstanceWrapper.get_by_tagvalue(tags, region)
    if not (instanceid or nametag or tags):
        raise ValueError('nametag, instanceid, or tags must be supplied.')

    return _list_annotating_decorator('hosts', [instancewrapper['public_dns_name']
        for instancewrapper in instancewrappers])
