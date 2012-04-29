AUTH = {}
PROFILES = {}
DEFAULT_REGION = 'eu-west-1'
CONFIG_DIR = 'config'
AMI = {}
EC2_DEFAULT_INSTANCE = None

# If this is True, it is possible to use the ``Name`` tag of EC2 instances
# to look up instances in Ec2Cache (which is used by --ec2name/-E).
# This feature requires that the ``Name`` tag is unique for all your EC2 instances.
EC2_SUPPORT_NAMETAG_LOOKUP = True


EC2_CACHE_FILE = '.awsfab_ec2cache'
EC2_REGIONS = ['eu-west-1']
