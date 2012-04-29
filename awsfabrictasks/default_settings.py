AUTH = {}
PROFILES = {}
DEFAULT_REGION = 'eu-west-1'
CONFIG_DIR = 'config'

# Default ssh user if the ``awsfab-ssh-user`` tag is not set
EC2_INSTANCE_DEFAULT_SSHUSER = 'root'

# Directories to search for "<key_name>.pem". These paths are filtered through
# os.path.expanduser, so paths like ``~/.ssh/`` works.
KEYPAIR_PATH = ['.', '~/.ssh/']
