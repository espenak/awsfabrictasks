# Config file for awsfabrictasks.
#
# This is a Python module, and it is imported just as a regular Python module.
# Every variable with an uppercase-only name is a setting.

AUTH = {'aws_access_key_id': 'XXXXXXXXXXXXXXXXXXXXXX',
        'aws_secret_access_key': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'}

DEFAULT_REGION = 'eu-west-1'


##################################################################
# Self documenting map of AMIs
# - You are not required to use this, but it makes it easier to read
#   EC2_LAUNCH_CONFIGS.
##################################################################
ami = {
    'ubuntu-10.04-lts': 'ami-fb665f8f'
}


###########################################################
# Configuration for ec2_launch_instance
###########################################################
EC2_LAUNCH_CONFIGS = {
    'ubuntu-10.04-lts-micro': {
        'description': 'Ubuntu 10.04 on the least expensive instance type.',

        # Ami ID (E.g.: ami-fb665f8f)
        'ami': ami['ubuntu-10.04-lts'],

        # One of: m1.small, m1.large, m1.xlarge, c1.medium, c1.xlarge, m2.xlarge, m2.2xlarge, m2.4xlarge, cc1.4xlarge, t1.micro
        'instance_type': 't1.micro',

        # List of security groups
        'security_groups': ['allowssh'],

        # Use the ``list_regions`` task to see all available regions
        'region': DEFAULT_REGION,

        # The name of the key pair to use for instances (See http://console.aws.amazon.com -> EC2 -> Key Pairs)
        'key_name': 'awstestkey',

        # The availability zone in which to launch the instances. This is
        # automatically prefixed by ``region``.
        'availability_zone': 'b',

        # Tags to add to the instances. You can use the ``ec2_*_tag`` tasks or
        # the management interface to manage tags. Special tags:
        #   - Name: Should not be in this dict. It is specified when launching
        #           an instance (needs to be unique for each instance).
        #   - awsfab-ssh-user: The ``awsfab`` tasks use this user to log into your instance.
        'tags': {
            'awsfab-ssh-user': 'ubuntu'
        }
    }
}



######################################################
# Add your own settings here
######################################################

MYCOOLSTUFF_REMOTE_DIR = '/var/www/stuff'
