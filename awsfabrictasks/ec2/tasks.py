"""
General tasks for AWS management.
"""
from pprint import pformat, pprint
from boto.ec2 import connect_to_region
from fabric.api import task, abort, local, env

from ..conf import awsfab_settings
from api import Ec2InstanceWrapper
from api import wait_for_stopped_state
from api import wait_for_running_state
from api import print_ec2_instance



__all__ = [
        'ec2_add_tag', 'ec2_set_tag', 'ec2_remove_tag',
        'ec2_launch_instance', 'ec2_start_instance', 'ec2_stop_instance',
        'ec2_list_instances', 'ec2_print_instance', 'ec2_login'
        ]



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
    if not awsfab_settings.EC2_LAUNCH_CONFIGS:
        abort('You have no awsfab_settings.EC2_LAUNCH_CONFIGS.')
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
    print_ec2_instance(instancewrapper.instance, full=full)

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
            print_ec2_instance(instance, full=full, indentspaces=11)


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
