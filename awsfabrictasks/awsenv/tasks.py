"""
Tasks for managing groups of AWS servers.
"""
from __future__ import print_function
from fabric.api import task

#from awsfabrictasks.conf import awsfab_settings
from awsfabrictasks.ec2.api import print_ec2_instance
from awsfabrictasks.rds.api import print_rds_instance
from .api import AwsEnvironment



__all__ = [
        'awsenv_print',
        ]


@task
def awsenv_print(environment):
    """
    Print information about all EC2 and RDS instances in the given AWS-environment.

    :param environment:
        The name of the environment.
    """
    awsenvironment = AwsEnvironment(environment)
    print('-' * 80)
    print('EC2 instances:')
    print('-' * 80)
    try:
        instancewrappers = awsenvironment.get_ec2_instancewrappers()
    except LookupError as e:
        print str(e)
    else:
        for instancewrapper in instancewrappers:
            print()
            print('{0}:'.format(instancewrapper.prettyname()))
            print_ec2_instance(instancewrapper.instance)

    print()
    print('-' * 80)
    print('RDS instances:')
    print('-' * 80)
    dbinstancewrappers = awsenvironment.get_rds_instancewrappers()
    for dbinstancewrapper in dbinstancewrappers:
        print()
        print_rds_instance(dbinstancewrapper.dbinstance)
