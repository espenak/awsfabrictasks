
#: The AWS access key. Should look something like this::
#:
#:    AUTH = {'aws_access_key_id': 'XXXXXXXXXXXXXXXXX',
#:            'aws_secret_access_key': 'aaaaaaaaaaaa\BBBBBBBBB\dsaddad'}
#:
AUTH = {}

#: The default AWS region to use with the commands where REGION is supported.
DEFAULT_REGION = 'eu-west-1'

#: Default ssh user if the ``awsfab-ssh-user`` tag is not set
EC2_INSTANCE_DEFAULT_SSHUSER = 'root'

#: Directories to search for "<key_name>.pem". These paths are filtered through
#: os.path.expanduser, so paths like ``~/.ssh/`` works.
KEYPAIR_PATH = ['.', '~/.ssh/']


#: Extra SSH arguments. Used with ``ssh`` and ``rsync``.
EXTRA_SSH_ARGS = '-o StrictHostKeyChecking=no'

#: Configuration for ec2_launch_instance (see the docs)
EC2_LAUNCH_CONFIGS = {}


#: S3 bucket suffix. This is used for all tasks taking bucketname as parameter.
#: The actual bucketname used become::
#:
#:      S3_BUCKET_PATTERN.format(bucketname=bucketname)
#:
#: This is typically used to add your domain name or company name to all bucket
#: names, but avoid having to type the entire name for each task. Examples::
#:
#:     S3_BUCKET_PATTERN = '{bucketname}.example.com'
#:     S3_BUCKET_PATTERN = 'example.com.{bucketname}'
#:
#: The default, ``"{bucketname}"``, uses the bucket name as provided by the
#: user without any changes.
#:
#: .. seealso::
#:      :meth:`awsfabrictasks.s3.api.S3ConnectionWrapper.get_bucket_using_pattern`,
#:      :func:`awsfabrictasks.s3.api.settingsformat_bucketname`
S3_BUCKET_PATTERN = '{bucketname}'
