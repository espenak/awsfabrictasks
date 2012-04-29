from os.path import join
from fabric import tasks

from .ec2 import cache
from .conf import awsfab_settings



def get_hosts_supporting_aws(self, arg_hosts, arg_roles, arg_exclude_hosts, env=None):
    hosts = tasks.Task.get_hosts(self, arg_hosts, arg_roles, arg_exclude_hosts, env)
    def splitnames(names):
        if names:
            return names.split(',')
        else:
            return []

    if env:
        if not env.key_filename:
            env.key_filename = []
    def add_host(cacheitem):
        host = cacheitem.get_ssh_uri()
        hosts.append(host)
        if env:
            env.key_filename.append(join(awsfab_settings.EC2_KEYDIR, '{key_name}.pem'.format(**cacheitem)))

    ids = splitnames(env.ec2id)
    for instanceid in ids:
        cacheitem = cache.get_by_instanceid(instanceid)
        add_host(cacheitem)
    names = splitnames(env.ec2name)
    for name in names:
        cacheitem = cache.get_by_nametag(name)
        add_host(cacheitem)
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
