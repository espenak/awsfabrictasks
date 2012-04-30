"""
General tasks for AWS management.
"""
from os.path import exists, join, expanduser, abspath
from pprint import pformat, pprint
from boto.ec2 import connect_to_region
from fabric.api import task, abort, local, env

from .conf import awsfab_settings



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

def parse_instanceid(instanceid_with_optional_region):
    if ':' in instanceid_with_optional_region:
        region, instanceid = instanceid_with_optional_region.split(':', 1)
    else:
        instanceid = instanceid_with_optional_region
        region = awsfab_settings.DEFAULT_REGION
    return region, instanceid

class Ec2InstanceWrapper(object):
    def __init__(self, instance):
        self.instance = instance

    def __getitem__(self, key):
        return getattr(self.instance, key)

    def __str__(self):
        return 'Ec2InstanceWrapper:{0}'.format(self.instance)

    def prettyname(self):
        instanceid = self.instance.id
        name = self.instance.tags.get('Name')
        if name:
            return '{instanceid} (name={name})'.format(**vars())
        else:
            return instanceid

    def get_ssh_uri(self):
        user = self['tags'].get('awsfab-ssh-user', awsfab_settings.EC2_INSTANCE_DEFAULT_SSHUSER)
        host = self['public_dns_name']
        return '{user}@{host}'.format(**vars())

    def get_ssh_key_filename(self):
        for dirpath in awsfab_settings.KEYPAIR_PATH:
            filename = abspath(join(expanduser(dirpath), self.instance.key_name + '.pem'))
            if exists(filename):
                return filename
        raise LookupError('Could not find {key_name} in awsfab_settings.')

    def add_instance_to_env(self):
        """
        Add ``self`` to ``fabric.api.env[self.get_ssh_uri()]``, and register
        the key-pair for the instance in ``fabric.api.env.key_filename``.
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
    def get_by_nametag(cls, name):
        if ':' in name:
            region, name = name.split(':', 1)
        else:
            region = awsfab_settings.DEFAULT_REGION
        connection = connect_to_region(region_name=region, **awsfab_settings.AUTH)
        if not connection:
            raise ValueError('Could not connect to region: {region}'.format(**vars()))
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
        region, instanceid = parse_instanceid(instanceid)
        connection = connect_to_region(region_name=region, **awsfab_settings.AUTH)
        if not connection:
            raise ValueError('Could not connect to region: {region}'.format(**vars()))
        reservations = connection.get_all_instances([instanceid])
        if len(reservations) == 0:
            raise LookupError('No ec2 instances with instanceid={0}'.format(instanceid))
        reservation = reservations[0]
        if len(reservation.instances) != 1:
            raise LookupError('Did not get exactly one instance with instanceid={0}'.format(instanceid))
        return cls(reservation.instances[0])

    @classmethod
    def get_from_host_string(cls):
        return env.ec2instances[env.host_string]



class WaitForStateError(Exception):
    """
    Raises when :func:`wait_for_state` times out.
    """


def wait_for_state(instanceid, state_name, sleep_intervals=[15, 5], last_sleep_repeat=20):

    from time import sleep

    region, instanceid = parse_instanceid(instanceid)
    sleep_intervals.extend([sleep_intervals[-1] for x in xrange(last_sleep_repeat)])
    max_wait_sec = sum(sleep_intervals)
    print 'Waiting for {instanceid} to change state to: "{state_name}. Will try for {max_wait_sec}s.".'.format(**vars())

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
    wait_for_state(instanceid, 'stopped', **kwargs)

def wait_for_running_state(instanceid, **kwargs):
    wait_for_state(instanceid, 'running', **kwargs)


def _print_instance(instance, full=False, indentspaces=3):
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


#@task
#def ec2_tag_instance_according_to_launchconfig(configname, name):
    #"""
    #Fix tagging if ``ec2_launch_instance`` is stopped while waiting for the instance to launch.
    #"""

@task
def ec2_add_tag(tagname, value=''):
    """
    Add tag to EC2 instance. Fails if tag already exists.

    :param tagname: Name of the tag to set (required).
    :param value: Value to set the tag to. Default to empty string.
    """
    instancewrapper = Ec2InstanceWrapper.get_from_host_string()
    if tagname in instancewrapper.instance.tags:
        prettyname = instancewrapper.prettyname()
        abort('{prettyname}: duplicate tag: {tagname}'.format(**vars()))
    instancewrapper.instance.add_tag(tagname, value)

@task
def ec2_set_tag(tagname, value=''):
    """
    Set tag on EC2 instance. Overwrites value if tag exists.

    :param tagname: Name of the tag to set (required).
    :param value: Value to set the tag to. Default to empty string.
    """
    instancewrapper = Ec2InstanceWrapper.get_from_host_string()
    instancewrapper.instance.add_tag(tagname, value)

@task
def ec2_remove_tag(tagname):
    """
    Remove tag from EC2 instance. Fails if tag does not exist.

    :param tagname: Name of the tag to remove (required).
    """
    instancewrapper = Ec2InstanceWrapper.get_from_host_string()
    if not tagname in instancewrapper.instance.tags:
        prettyname = instancewrapper.prettyname()
        abort('{prettyname} has no "{tagname}"-tag'.format(**vars()))
    instancewrapper.instance.remove_tag(tagname)



@task
def ec2_launch_instance(name, configname=None, noconfirm=False):
    """
    Launch new EC2 instance.

    :param name: The name to tag the EC2 instance with (required)
    :param configname: Name of the configuration in
        ``awsfab_settings.EC2_LAUNCH_CONFIGS``. Prompts for input if not
        provided as an argument.
    :param noconfirm: Do not require the user to confirm creating the instance?
        Defaults to ``False``.
    """

    if not configname:
        print 'Please select one of the following configurations:'
        for config in awsfab_settings.EC2_LAUNCH_CONFIGS:
            print '-', config
        configname = raw_input('Type name of config: ').strip()
    if not configname in awsfab_settings.EC2_LAUNCH_CONFIGS:
        abort('"{configname}" is not in awsfab_settings.EC2_LAUNCH_CONFIGS'.format(**vars()))

    conf = awsfab_settings.EC2_LAUNCH_CONFIGS[configname]
    ami_image_id = conf['ami']
    key_pair_name = conf['key_name']
    kw = dict(
            key_name = conf['key_name'],
            instance_type = conf['instance_type'],
            security_groups = conf['security_groups'])
    if 'availability_zone' in conf:
        kw['placement'] = conf['region'] + conf['availability_zone']

    print ('Are you sure you want to launch (create) a new instance named '
        '"{name}" with the following settings and tags?').format(**vars())
    pprint(kw)
    print 'tags:', pformat(conf['tags'])
    if raw_input('Create instance [y/N]? ').lower() != 'y':
        abort('Aborted')

    connection = connect_to_region(region_name=conf['region'], **awsfab_settings.AUTH)
    reservation = connection.run_instances(conf['ami'], **kw)
    instance = reservation.instances[0]
    instance.add_tag('Name', name)
    if 'tags' in conf:
        for tagname, value in conf['tags'].iteritems():
            instance.add_tag(tagname, value)
    wait_for_running_state(instance.id)


@task
def ec2_start_instance(nowait=False):
    """
    Start EC2 instance.

    :param nowait: Set to ``True`` to let the EC2 instance start in the
        background instead of waiting for it to start. Defaults to ``False``.
    """
    instancewrapper = Ec2InstanceWrapper.get_from_host_string()
    instancewrapper.instance.start()
    if nowait:
        print ('Starting: {id}. This is an asynchronous operation. Use '
                '``ec2_list_instances`` or the aws dashboard to check the status of '
                'the operation.').format(id=instancewrapper['id'])
    else:
        wait_for_running_state(instancewrapper['id'])

@task
def ec2_stop_instance(nowait=False):
    """
    Stop EC2 instance.

    :param nowait: Set to ``True`` to let the EC2 instance stop in the
        background instead of waiting for it to start. Defaults to ``False``.
    """
    instancewrapper = Ec2InstanceWrapper.get_from_host_string()
    instancewrapper.instance.stop()
    if nowait:
        print ('Stopping: {id}. This is an asynchronous operation. Use '
                '``ec2_list_instances`` or the aws dashboard to check the status of '
                'the operation.').format(id=instancewrapper['id'])
    else:
        wait_for_stopped_state(instancewrapper['id'])

@task
def ec2_print_instance(full=False):
    """
    Print EC2 instance info.

    :param full: Print all attributes, or just the most useful ones? Defaults
        to ``False``.
    """
    instancewrapper = Ec2InstanceWrapper.get_from_host_string()
    print 'Instance:', instancewrapper['id']
    _print_instance(instancewrapper.instance, full=full)

@task
def ec2_list_instances(region=awsfab_settings.DEFAULT_REGION, full=False):
    """
    List EC2 instances in a region (defaults to awsfab_settings.DEFAULT_REGION).

    :param region: The region to list instances in. Defaults to
        ``awsfab_settings.DEFAULT_REGION.
    :param full: Print all attributes, or just the most useful ones? Defaults
        to ``False``.
    """
    conn = connect_to_region(region_name=region, **awsfab_settings.AUTH)

    for reservation in conn.get_all_instances():
        print
        print 'id:', reservation.id
        print '   owner_id:', reservation.owner_id
        print '   groups:'
        for group in reservation.groups:
            print '      - {name} (id:{id})'.format(**group.__dict__)
        print '   instances:'
        for instance in reservation.instances:
            attrnames = None
            print '      - id:', instance.id
            _print_instance(instance, full=full, indentspaces=11)


@task
def ec2_login():
    """
    Log into the host specified by --hosts, --ec2names or --ec2ids.

    Aborts if more than one host is specified.
    """
    if len(env.all_hosts) != 1:
        abort('ec2_login only works with exactly one host. Given hosts: {0}'.format(repr(env.all_hosts)))
    instancewrapper = Ec2InstanceWrapper.get_from_host_string()
    host = instancewrapper.get_ssh_uri()
    key_filename = instancewrapper.get_ssh_key_filename()
    cmd = 'ssh -i {key_filename} {host}'.format(**vars())
    local(cmd)
