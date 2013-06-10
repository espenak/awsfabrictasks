from fabric.api import env
from .ec2.api import Ec2InstanceWrapper

version = '1.1.1'


def expand_roledefs():
    for k, v in env.roledefs.iteritems():
        if isinstance(v, dict):
            if 'ec2:tagged' in v:
                region = v['ec2:tagged'].pop('region') if 'region' in v['ec2:tagged'] else None
                instancewrappers = Ec2InstanceWrapper.get_by_tagvalue(v['ec2:tagged'], region)
                env.roledefs[k] = [instancewrapper['public_dns_name'] for instancewrapper in instancewrappers]
