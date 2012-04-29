from os.path import join
from fabric import tasks

from .ec2 import Ec2InstanceWrapper
from .conf import awsfab_settings


def _splitnames(names):
    if names:
        return names.split(',')
    else:
        return []

def get_hosts_supporting_aws(self, arg_hosts, arg_roles, arg_exclude_hosts, env=None):
    hosts = tasks.Task.get_hosts(self, arg_hosts, arg_roles, arg_exclude_hosts, env)

    ids = _splitnames(env.ec2id)
    for instanceid in ids:
        instance = Ec2InstanceWrapper.get_by_instanceid(instanceid)
        instance.add_instance_to_env()
        hosts.append(instance.get_ssh_uri())

    names = _splitnames(env.ec2name)
    for name in names:
        instance = Ec2InstanceWrapper.get_by_nametag(name)
        instance.add_instance_to_env()
        hosts.append(instance.get_ssh_uri())
    return hosts


def monkey_patch_get_hosts():
    tasks.WrappedCallableTask.get_hosts = get_hosts_supporting_aws

def awsfab():
    monkey_patch_get_hosts()
    from optparse import make_option
    from fabric.main import main
    from fabric import state

    state.env_options.append(
            make_option('-E', '--ec2name',
                default=None,
                help="Name of AWS host."
                )
            )
    state.env_options.append(
            make_option('--ec2id',
                default=None,
                help="ID of AWS host."
                )
            )

    main()
