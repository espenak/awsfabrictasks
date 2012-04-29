from fabric import tasks



def get_hosts_supporting_aws(self, arg_hosts, arg_roles, arg_exclude_hosts, env=None):
    hosts = tasks.Task.get_hosts(self, arg_hosts, arg_roles, arg_exclude_hosts, env)
    print env.ec2name
    print hosts
    return hosts

def monkey_patch_get_hosts():
    tasks.WrappedCallableTask.get_hosts = get_hosts_supporting_aws

def awsfab():
    monkey_patch_get_hosts()
    from optparse import make_option
    from fabric.main import main
    from fabric import state
    from .conf import awsfab_settings
    from .ec2 import cache

    state.env_options.append(
            make_option('-E', '--ec2name',
                action='append',
                default=None,
                help="Name of AWS host."
                )
            )
    state.env_options.append(
            make_option('--ec2id',
                action='append',
                default=None,
                help="ID of AWS host."
                )
            )

    main()
