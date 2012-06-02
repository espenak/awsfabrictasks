#from pprint import pformat
from boto.s3.prefix import Prefix
from fnmatch import fnmatchcase
from boto.s3.connection import S3Connection

from awsfabrictasks.conf import awsfab_settings


class S3ConnectionError(Exception):
    """
    Raised when we fail to connect to S3.
    """
    def __init__(self, msg='Could not connect S3'):
        super(S3ConnectionError, self).__init__(msg)


def settingsformat_bucketname(bucketname):
    """
    Returns ``awsfab_settings.S3_BUCKET_PATTERN.format(bucketname=bucketname)``.

    .. seealso:: :obj:`awsfabrictasks.default_settings.S3_BUCKET_PATTERN`.
    """
    return awsfab_settings.S3_BUCKET_PATTERN.format(bucketname=bucketname)


class S3ConnectionWrapper(object):
    """
    S3 connection wrapper.
    """
    def __init__(self, connection):
        """
        :param bucket: A :class:`boto.rds.bucket.DBInstance` object.
        """
        self.connection = connection

    def __str__(self):
        return 'S3ConnectionWrapper:{0}'.format(self.connection)

    @classmethod
    def get_connection(cls):
        """
        Connect to S3 using ``awsfab_settings.AUTH``.

        :return: S3ConnectionWrapper object.
        """
        connection = S3Connection(**awsfab_settings.AUTH)
        return cls(connection)

    @classmethod
    def get_bucket_using_pattern(cls, bucketname):
        """
        Same as :meth:`.get_bucket`, however the ``bucketname`` is filtered
        through :func:`.settingsformat_bucketname`.
        """
        return cls.get_bucket(settingsformat_bucketname(bucketname))

    @classmethod
    def get_bucket(cls, bucketname):
        """
        Get the requested bucket.

        Shortcut for::

            S3ConnectionWrapper.get_connection().connection.get_bucket(bucketname)

        :param bucketname: Name of an S3 bucket.
        """
        connectionwrapper = S3ConnectionWrapper.get_connection()
        return connectionwrapper.connection.get_bucket(bucketname)



def iter_bucketcontents(bucket, prefix, match, delimiter, formatter=lambda key: key.name):
    """
    Iterate over items given bucket, yielding items formatted for output.

    :param bucket: A class:`boto.s3.bucket.Bucket` object.
    :param prefix:
        The prefix to list. Defaults to empty string, which lists
        all items in the root directory.
    :param match:
        A Unix shell style pattern to match. Matches against the entire key
        name (in filesystem terms: the absolute path).

        Uses the ``fnmatch`` python module. The match is case-sensitive.

        Examples::

            *.jpg
            *2012*example*.log
            icon-*.png

    :param delimiter:
        The delimiter to use. Defaults to ``/``.

    :param formatter:
        Formatter callback to use to format each key. Not used on Prefix-keys
        (directories).  The callback should take a key as input, and return a
        string.

    .. seealso:: http://docs.amazonwebservices.com/AmazonS3/latest/dev/ListingKeysHierarchy.html
    """
    for key in bucket.list(prefix=prefix, delimiter=delimiter):
        if match and not fnmatchcase(key.name, match):
            continue
        if isinstance(key, Prefix):
            yield key.name
        else:
            yield formatter(key)
