#from pprint import pformat
from hashlib import sha256
from fnmatch import fnmatchcase
from boto.s3.connection import S3Connection
from boto.s3.prefix import Prefix
from boto.s3.key import Key

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


class S3ErrorBase(Exception):
    """
    Base class for all S3 errors. Never raised directly.
    """

class S3FileErrorBase(S3ErrorBase):
    """
    Base class for all :class:`S3File` errors. Never raised directly.
    """
    def __init__(self, s3file):
        """
        :param s3file: A :class:`S3File` object.
        """
        self.s3file = s3file

    def __str__(self):
        return '{classname}: {s3file}'.format(classname=self.__class__.__name__,
                                              s3file=self.s3file)

class S3FileExistsError(S3FileErrorBase):
    """
    Raised when trying to overwrite an existing :class:`S3File`, unless
    overwriting is requested.
    """

class S3FileDoesNotExist(S3FileErrorBase):
    """
    Raised when an :class:`S3File` does not exist.
    """

class S3File(object):
    def __init__(self, bucket, name):
        self.bucket = bucket
        self.name = name
        self.key = Key(bucket)
        self.key.name = name

    def _overwrite_check(self, overwrite):
        if not overwrite and self.key.exists():
            raise S3FileExistsError(self)

    def get_metadata(self, metadata_name):
        return self.key.get_metadata(metadata_name)

    def get_checksum(self):
        return self.get_metadata('awsfabchecksum')

    def exists(self):
        """
        Return ``True`` if the key/file exists in the S3 bucket.
        """
        return self.key.exists()

    def delete(self):
        """
        Delete the key/file from the bucket.

        :raise S3FileDoesNotExist:
            If the key does not exist in the bucket.
        """
        if not self.exists():
            raise S3FileDoesNotExist(self)
        self.key.delete()

    def set_contents_from_string(self, data, overwrite=False):
        """
        Write ``data`` to the S3 file.

        :param overwrite:
            If ``True``, overwrite if the key/file exists.
        :raise S3FileExistsError:
            If ``overwrite==True`` and the key exists in the bucket.
        """
        self._overwrite_check(overwrite)
        self.key.set_contents_from_string(data)

    def set_contents_from_filename(self, localfile, overwrite=False):
        """
        Upload ``localfile``.

        :param overwrite:
            If ``True``, overwrite if the key/file exists.
        :raise S3FileExistsError:
            If ``overwrite==True`` and the key exists in the bucket.
        """
        self._overwrite_check(overwrite)
        self.key.set_contents_from_filename(localfile)

    def get_contents_as_string(self):
        """
        Download the file and return it as a string.
        """
        return self.key.get_contents_as_string()

    def get_contents_to_filename(self, localfile):
        """
        Download the file to the given ``localfile``.
        """
        self.key.get_contents_to_filename(localfile)

    def __str__(self):
        return '{classname}({bucket}, {name})'.format(classname=self.__class__.__name__,
                                                      **self.__dict__)


#class S3Sync(object):

    #def __init__(self, bucketname, local_dir, remote_dir):
        #self.bucketname = bucketname
        #self.local_dir = local_dir
        #self.remote_dir = remote_dir
