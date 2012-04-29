"""
General tasks for AWS management.
"""
from fabric.api import task, abort, local, env
from pprint import pformat
from boto.ec2 import connect_to_region

from .conf import awsfab_settings
from .utils import format_keypairs_for_ssh_options


class Ec2InstanceWrapper(object):
    def __init__(self, instance):
        self.instance = instance

    def __getitem__(self, key):
        return getattr(self.instance, key)

    def __str__(self):
        return 'Ec2InstanceWrapper:{0}'.format(self.instance)

    def get_ssh_uri(self):
        user = self['tags'].get('awsfab-ssh-user', awsfab_settings.EC2_INSTANCE_DEFAULT_SSHUSER)
        host = self['public_dns_name']
        return '{user}@{host}'.format(**vars())

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
        for key in awsfab_settings.get_key_filenames(self.instance.key_name):
            if not key in env.key_filename:
                env.key_filename.append(key)

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
        if ':' in instanceid:
            region, instanceid = instanceid.split(':', 1)
        else:
            region = awsfab_settings.DEFAULT_REGION
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



def _print_instance(instance, attrnames=None, indentspaces=3):
    indent = ' ' * indentspaces
    if not attrnames:
        attrnames = sorted(instance.__dict__.keys())
    for attrname in attrnames:
        if attrname.startswith('_'):
            continue
        value = instance.__dict__[attrname]
        if not isinstance(value, (str, unicode, bool, int)):
            value = pformat(value)
        print '{indent}{attrname}: {value}'.format(**vars())


@task
def ec2_launch_instance(configname):
    """
    Launch new EC2 instance.

    ``ec2_launch_instance:<configname>``, where ``configname`` is a key in
    ``awsfab_settings.EC2_LAUNCH_CONFIGS``.
    """
    conf = awsfab_settings.EC2_LAUNCH_CONFIGS[configname]
    connection = connect_to_region(region_name=conf['region'], **awsfab_settings.AUTH)
    ami_image_id = conf['ami']
    key_pair_name = conf['key_name']
    connection.run_instances(conf['ami'],
                             key_name=conf['key_name'],
                             instance_type=conf['instance_type'],
                             security_groups=conf['security_groups'])


@task
def ec2_start_instance():
    instance = Ec2InstanceWrapper.get_from_host_string()
    stopped = instance.instance.start()
    print ('Starting: {id}. This is an asynchronous operation. Use '
            '``ec2_list_instances`` or the aws dashboard to check the status of '
            'the operation.').format(id=instance['id'])

@task
def ec2_stop_instance():
    instance = Ec2InstanceWrapper.get_from_host_string()
    stopped = instance.instance.stop()
    print ('Stopping: {id}. This is an asynchronous operation. Use '
            '``ec2_list_instances`` or the aws dashboard to check the status of '
            'the operation.').format(id=instance['id'])

@task
def ec2_list_instances(full=False, region=awsfab_settings.DEFAULT_REGION):
    """
    List EC2 instances in a region. Use ``list_instances:full=true`` for more details.
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
            if not full:
                attrnames = ['state', 'instance_type', 'ip_address',
                             'dns_name', 'key_name', 'tags', 'placement']
            print '      - id:', instance.id
            _print_instance(instance, attrnames=attrnames, indentspaces=11)


@task
def ec2_login():
    """
    Log into the host specified by --hosts, --ec2names or --ec2ids.

    Aborts if more than one host is specified.
    """
    if len(env.all_hosts) != 1:
        abort('ec2_login only works with exactly one host. Given hosts: {0}'.format(repr(env.all_hosts)))
    host = env.host_string
    keys = format_keypairs_for_ssh_options()
    cmd = 'ssh {keys} {host}'.format(**vars())
    local(cmd)
