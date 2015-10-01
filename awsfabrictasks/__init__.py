version = '1.3.0b1'


def expand_roledefs():
    from fabric.api import env
    from awsfabrictasks.ec2.api import Ec2InstanceWrapper
    for k, v in env.roledefs.items():
        if isinstance(v, dict):
            if 'ec2:tagged' in v:
                region = v['ec2:tagged'].pop('region') if 'region' in v['ec2:tagged'] else None
                instancewrappers = Ec2InstanceWrapper.get_by_tagvalue(v['ec2:tagged'], region)
                env.roledefs[k] = [instancewrapper['public_dns_name'] for instancewrapper in instancewrappers]
