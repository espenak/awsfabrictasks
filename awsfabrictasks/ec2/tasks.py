"""
General tasks for AWS management.
"""
from __future__ import print_function

from pprint import pformat, pprint
from boto.ec2 import connect_to_region
from fabric.api import task, abort, local, env
from fabric.contrib.console import confirm
from textwrap import fill

from awsfabrictasks.conf import awsfab_settings
from awsfabrictasks.utils import force_slashend
from awsfabrictasks.utils import parse_bool
from .api import Ec2InstanceWrapper
from .api import wait_for_stopped_state
from .api import wait_for_running_state
from .api import print_ec2_instance
from .api import Ec2LaunchInstance
from .api import ec2_rsync_upload
from .api import ec2_rsync_upload_command
from .api import ec2_rsync_download
from .api import ec2_rsync_download_command



__all__ = [
        'ec2_add_tag', 'ec2_set_tag', 'ec2_remove_tag',
        'ec2_launch_instance', 'ec2_start_instance', 'ec2_stop_instance',
        'ec2_list_instances', 'ec2_print_instance', 'ec2_login',
        'ec2_rsync_download_dir', 'ec2_rsync_upload_dir'
        ]



@task
def ec2_rsync_download_dir(remote_dir, local_dir, rsync_args='-av', noconfirm=False):
    """
    Sync the contents of ``remote_dir`` into ``local_dir``. E.g.: if ``remote_dir`` is
    ``/etc``, and ``local_dir`` is ``/tmp``, the ``/tmp/etc`` will be created on the local
    host, and filled with all files in ``/etc`` on the EC2 instance.

    :param remote_dir: The remote directory to download into local_dir.
    :param local_dir: The local directory.
    :param rsync_args: Arguments for ``rsync``. Defaults to ``-av``.
    :param noconfirm:
        If this is ``True``, we will not ask for confirmation before
        proceeding with the operation. Defaults to ``False``.
    """
    kwargs = dict(remote_dir=remote_dir,
                  local_dir=local_dir,
                  rsync_args=rsync_args)
    if not parse_bool(noconfirm):
        instancewrapper = Ec2InstanceWrapper.get_from_host_string()
        print('Are you sure you want to run:')
        print('   ', ec2_rsync_download_command(instancewrapper, **kwargs))
        if not confirm('Proceed?'):
            abort('Aborted')
    ec2_rsync_download(**kwargs)

@task
def ec2_rsync_upload_dir(local_dir, remote_dir, rsync_args='-av', noconfirm=False):
    """
    Sync the contents of ``local_dir`` into ``remote_dir`` on the EC2
    instance. E.g.: if ``local_dir`` is ``/etc``, and ``remote_dir`` is
    ``/tmp``, the ``/tmp/etc`` will be created on the EC2 instance, and filled
    with all files in ``/etc`` on the local host.

    :param local_dir: The local directory to upload to the EC2 instance.
    :param remote_dir: The remote directory to upload local_dir into.
    :param rsync_args: Arguments for ``rsync``. Defaults to ``-av``.
    :param noconfirm:
        If this is ``True``, we will not ask for confirmation before
        proceeding with the operation. Defaults to ``False``.
    """
    kwargs = dict(local_dir=local_dir,
                  remote_dir=remote_dir,
                  rsync_args=rsync_args)
    if not parse_bool(noconfirm):
        instancewrapper = Ec2InstanceWrapper.get_from_host_string()
        print('Are you sure you want to run:')
        print('   ', ec2_rsync_upload_command(instancewrapper, **kwargs))
        if not confirm('Proceed?'):
            abort('Aborted')
    ec2_rsync_upload(**kwargs)

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
def ec2_launch_instance(name, configname=None):
    """
    Launch new EC2 instance.

    :param name: The name to tag the EC2 instance with (required)
    :param configname: Name of the configuration in
        ``awsfab_settings.EC2_LAUNCH_CONFIGS``. Prompts for input if not
        provided as an argument.
    """
    launcher = Ec2LaunchInstance(extra_tags={'Name': name}, configname=configname)
    launcher.confirm()
    instance = launcher.run_instance()
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
        print(('Starting: {id}. This is an asynchronous operation. Use '
                '``ec2_list_instances`` or the aws dashboard to check the status of '
                'the operation.').format(id=instancewrapper['id']))
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
        print(('Stopping: {id}. This is an asynchronous operation. Use '
                '``ec2_list_instances`` or the aws dashboard to check the status of '
                'the operation.').format(id=instancewrapper['id']))
    else:
        wait_for_stopped_state(instancewrapper['id'])

def _get_instanceident(instance):
    return 'id: {id}   (Name: {name})'.format(id=instance.id,
                                          name=instance.tags.get('Name', ''))

@task
def ec2_print_instance(full=False):
    """
    Print EC2 instance info.

    :param full: Print all attributes, or just the most useful ones? Defaults
        to ``False``.
    """
    instancewrapper = Ec2InstanceWrapper.get_from_host_string()
    print('Instance:', _get_instanceident(instancewrapper.instance))
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
        print()
        print('id:', reservation.id)
        print('   owner_id:', reservation.owner_id)
        print('   groups:')
        for group in reservation.groups:
            print('      - {name} (id:{id})'.format(**group.__dict__))
        print('   instances:')
        for instance in reservation.instances:
            attrnames = None
            print('      -', _get_instanceident(instance))
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
    extra_ssh_args = awsfab_settings.EXTRA_SSH_ARGS
    cmd = 'ssh -i {key_filename} {extra_ssh_args} {host}'.format(**vars())
    local(cmd)
