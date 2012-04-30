from os.path import exists, join, expanduser, abspath
from pprint import pformat, pprint
from boto.ec2 import connect_to_region
from fabric.api import local, env

from ..conf import awsfab_settings



def ec2_rsync(local_dir, remote_dir, rsync_args='-av', sync_content=False):
    """
    rsync ``local_dir`` into ``remote_dir`` on the current EC2 instance (the
    one returned by :meth:`Ec2InstanceWrapper.get_from_host_string`).

    :param sync_content: Normally the function automatically makes sure
        ``local_dir`` is not suffixed with ``/``, which makes rsync copy
        ``local_dir`` into ``remote_dir``. With ``sync_content=True``,
        the content of ``local_dir`` is synced into ``remote_dir`` instead.
    """
    instance = Ec2InstanceWrapper.get_from_host_string()
    ssh_uri = instance.get_ssh_uri()
    key_filename = instance.get_ssh_key_filename()
    if sync_content:
        if not local_dir.endswith('/'):
            local_dir = local_dir + '/'
    else:
        if local_dir.endswith('/'):
            local_dir = local_dir.rstrip('/')
    rsync_cmd = 'rsync {rsync_args} -e "ssh -i {key_filename}" {local_dir} {ssh_uri}:{remote_dir}'.format(**vars())
    local(rsync_cmd)

def _parse_instanceident(instanceid_with_optional_region):
    if ':' in instanceid_with_optional_region:
        region, instanceid = instanceid_with_optional_region.split(':', 1)
    else:
        instanceid = instanceid_with_optional_region
        region = awsfab_settings.DEFAULT_REGION
    return region, instanceid


def parse_instanceid(instanceid_with_optional_region):
    """
    Parse instance id with an optional region-name prefixed. Region name
    is specified by prefixing the instanceid with ``<regionname>:``.

    :return: (region, instanceid) where region defaults to
        ``awsfab_settings.DEFAULT_REGION`` if not prefixed to the id.
    """
    return _parse_instanceident(instanceid_with_optional_region)

def parse_instancename(instancename_with_optional_region):
    """
    Just like :func:`parse_instanceid`, however this is for instance names.
    We keep them as separate functions in case they diverge in the future.

    :return: (region, instanceid) where region defaults to
        ``awsfab_settings.DEFAULT_REGION`` if not prefixed to the name.
    """
    return _parse_instanceident(instancename_with_optional_region)


class Ec2RegionConnectionError(Exception):
    """
    Raised when we fail to connect to a region.
    """
    def __init__(self, region):
        self.region = region
        msg = 'Could not connect to region: {region}'.format(**vars())
        super(Ec2RegionConnectionError, self).__init__(msg)

class Ec2InstanceWrapper(object):
    """
    Wraps a :class:`boto.ec2.instance.Instance` with convenience functions.

    :ivar instance: The :class:`boto.ec2.instance.Instance`.
    """
    def __init__(self, instance):
        """
        :param instance: A :class:`boto.ec2.instance.Instance` object.
        """
        self.instance = instance

    def __getitem__(self, key):
        """
        Provides easy access to attributes in ``self.instance``.
        """
        return getattr(self.instance, key)

    def __str__(self):
        return 'Ec2InstanceWrapper:{0}'.format(self)

    def prettyname(self):
        """
        Return a pretty-formatted name for this instance, using the Name-tag if
        the instance is tagged with it.
        """
        instanceid = self.instance.id
        name = self.instance.tags.get('Name')
        if name:
            return '{instanceid} (name={name})'.format(**vars())
        else:
            return instanceid

    def get_ssh_uri(self):
        """
        Get the SSH URI for the instance.

        :return: "<instance.tags['awsfab-ssh-user']>@<instance.public_dns_name>"
        """
        user = self['tags'].get('awsfab-ssh-user', awsfab_settings.EC2_INSTANCE_DEFAULT_SSHUSER)
        host = self['public_dns_name']
        return '{user}@{host}'.format(**vars())

    def get_ssh_key_filename(self):
        """
        Get the SSH indentify filename (.pem-file) for the instance. Searches
        ``awsfab_settings.KEYPAIR_PATH`` for ``"<instance.key_name>.pem"``.

        :raise LookupError: If the 
        """
        path = awsfab_settings.KEYPAIR_PATH
        for dirpath in path:
            filename = abspath(join(expanduser(dirpath), self.instance.key_name + '.pem'))
            if exists(filename):
                return filename
        raise LookupError('Could not find {key_name} in awsfab_settings.KEYPAIR_PATH: {path!r}'.format(**vars()))

    def add_instance_to_env(self):
        """
        Add ``self`` to ``fabric.api.env.ec2instances[self.get_ssh_uri()]``,
        and register the key-pair for the instance in
        ``fabric.api.env.key_filename``.
        """
        if not 'ec2instances' in env:
            env['ec2instances'] = {}
        env['ec2instances'][self.get_ssh_uri()] = self
        if not env.key_filename:
            env.key_filename = []
        key_filename = self.get_ssh_key_filename()
        if not key_filename in env.key_filename:
            env.key_filename.append(key_filename)

    @classmethod
    def get_by_nametag(cls, instancename_with_optional_region):
        """
        Connect to AWS and get the EC2 instance with the given Name-tag.

        :param instancename_with_optional_region:
            Parsed with :func:`parse_instancename` to find the region and name.
        :raise Ec2RegionConnectionError: If connecting to the region fails.
        :raise LookupError: If the requested instance was not found in the region.
        :return: A :class:`Ec2InstanceWrapper` contaning the requested instance.
        """
        region, name = parse_instancename(instancename_with_optional_region)
        connection = connect_to_region(region_name=region, **awsfab_settings.AUTH)
        if not connection:
            raise Ec2RegionConnectionError(region)
        reservations = connection.get_all_instances(filters={'tag:Name': name})
        if len(reservations) == 0:
            raise LookupError('No ec2 instances with tag:Name={0}'.format(name))
        if len(reservations) > 1:
            raise LookupError('More than one ec2 reservations with tag:Name={0}'.format(name))
        reservation = reservations[0]
        if len(reservation.instances) != 1:
            raise LookupError('Did not get exactly one instance with tag:Name={0}'.format(name))
        return cls(reservation.instances[0])

    @classmethod
    def get_by_instanceid(cls, instanceid):
        """
        Connect to AWS and get the EC2 instance with the given instance ID.

        :param instanceid_with_optional_region:
            Parsed with :func:`parse_instanceid` to find the region and name.
        :raise Ec2RegionConnectionError: If connecting to the region fails.
        :raise LookupError: If the requested instance was not found in the region.
        :return: A :class:`Ec2InstanceWrapper` contaning the requested instance.
        """
        region, instanceid = parse_instanceid(instanceid)
        connection = connect_to_region(region_name=region, **awsfab_settings.AUTH)
        if not connection:
            raise Ec2RegionConnectionError(region)
        reservations = connection.get_all_instances([instanceid])
        if len(reservations) == 0:
            raise LookupError('No ec2 instances with instanceid={0}'.format(instanceid))
        reservation = reservations[0]
        if len(reservation.instances) != 1:
            raise LookupError('Did not get exactly one instance with instanceid={0}'.format(instanceid))
        return cls(reservation.instances[0])

    @classmethod
    def get_from_host_string(cls):
        """
        If an instance has been registered in ``fabric.api.env`` using
        :meth:`add_instance_to_env`, this method can be used to get
        the instance identified by ``fabric.api.env.host_string``.
        """
        return env.ec2instances[env.host_string]



class WaitForStateError(Exception):
    """
    Raises when :func:`wait_for_state` times out.
    """


def wait_for_state(instanceid, state_name, sleep_intervals=[15, 5], last_sleep_repeat=40):
    """
    Poll the instance with ``instanceid`` until its ``state_name`` matches the
    desired ``state_name``.

    The first poll is performed without any delay, and the rest of the polls are
    performed according to ``sleep_intervals``.

    :param instanceid: ID of an instance.
    :param state_name: The state_name to wait for.
    :param sleep_intervals: List of seconds to wait between each poll for state. The first poll
        is made immediately, then we wait for sleep_intervals[0] seconds before the next poll,
        and repeat for each item in sleep_intervals. Then we repeat for ``last_sleep_repeat``
        using the last item in ``sleep_intervals`` as the timout for each wait.
    :param last_sleep_repeat:
        Number of times to repeat the last item in ``sleep_intervals``. If this
        is 20, we will wait for a maximum of ``sum(sleep_intervals) + sleep_intervals[-1]*20``.
    """
    from time import sleep
    region, instanceid = parse_instanceid(instanceid)
    sleep_intervals.extend([sleep_intervals[-1] for x in xrange(last_sleep_repeat)])
    max_wait_sec = sum(sleep_intervals)
    print 'Waiting for {instanceid} to change state to: "{state_name}". Will try for {max_wait_sec}s.'.format(**vars())

    sleep_intervals_len = len(sleep_intervals)
    for index, sleep_sec in enumerate(sleep_intervals):
        instancewrapper = Ec2InstanceWrapper.get_by_instanceid(instanceid)
        current_state_name = instancewrapper['state']
        if current_state_name == state_name:
            print '.. OK'
            return
        index_n1 = index + 1
        print '.. Current state: "{current_state_name}". Next poll ({index_n1}/{sleep_intervals_len}) for "{state_name}"-state in {sleep_sec}s.'.format(**vars())
        sleep(sleep_sec)
    raise WaitForStateError('Desired state, "{state_name}", not achieved in {max_wait_sec}s.'.format(**vars()))


def wait_for_stopped_state(instanceid, **kwargs):
    """
    Shortcut for ``wait_for_state(instanceid, 'stopped', **kwargs)``.
    """
    wait_for_state(instanceid, 'stopped', **kwargs)

def wait_for_running_state(instanceid, **kwargs):
    """
    Shortcut for ``wait_for_state(instanceid, 'running', **kwargs)``.
    """
    wait_for_state(instanceid, 'running', **kwargs)


def print_ec2_instance(instance, full=False, indentspaces=3):
    """
    Print attributes of an ec2 instance.

    :param instance: A :class:`boto.ec2.instance.Instance` object.
    :param full: Print all attributes? If not, a subset of the attributes are printed.
    :param indentspaces: Number of spaces to indent each line in the output.
    """
    indent = ' ' * indentspaces
    if full:
        attrnames = sorted(instance.__dict__.keys())
    else:
        attrnames = ['state', 'instance_type', 'ip_address',
                     'public_dns_name', 'key_name', 'tags', 'placement']
    for attrname in attrnames:
        if attrname.startswith('_'):
            continue
        value = instance.__dict__[attrname]
        if not isinstance(value, (str, unicode, bool, int)):
            value = pformat(value)
        print '{indent}{attrname}: {value}'.format(**vars())
