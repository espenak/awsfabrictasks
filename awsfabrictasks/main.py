from os.path import join
from fabric import tasks

from .ec2.api import Ec2InstanceWrapper
from .conf import awsfab_settings


def _splitnames(names):
    if names:
        return names.split(',')
    else:
        return []

def get_hosts_supporting_aws(self, arg_hosts, arg_roles, arg_exclude_hosts, env=None):
    hosts = tasks.Task.get_hosts(self, arg_hosts, arg_roles, arg_exclude_hosts, env)

    ids = _splitnames(env.ec2ids)
    for instanceid in ids:
        instance = Ec2InstanceWrapper.get_by_instanceid(instanceid)
        instance.add_instance_to_env()
        hosts.append(instance.get_ssh_uri())

    names = _splitnames(env.ec2names)
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
            make_option('-E', '--ec2names',
                default=None,
                help=('Comma-separated list of AWS hosts identified by their '
                    '``Name`` tag. You can specify region by prefixing the name '
                    'with ``region:`` (e.g.: eu-west-1:ec2test). Default region '
                    'is awsfab_settings.DEFAULT_REGION ({0}).'.format(awsfab_settings.DEFAULT_REGION))
                )
            )
    state.env_options.append(
            make_option('--ec2ids',
                default=None,
                help=('Comma-separated list of AWS hosts identified by instance ID. '
                    'You can specify region by prefixing the instanceid '
                    'with ``region:`` (e.g.: eu-west-1:x-abcdefg). Default region '
                    'is awsfab_settings.DEFAULT_REGION ({0}).'.format(awsfab_settings.DEFAULT_REGION))
                )
            )

    main()
