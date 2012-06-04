#from pprint import pformat
from fnmatch import fnmatchcase
from os import walk, makedirs
from os.path import join, abspath, exists, dirname
from boto.s3.connection import S3Connection
from boto.s3.prefix import Prefix
from boto.s3.key import Key

from awsfabrictasks.utils import force_slashend
from awsfabrictasks.utils import localpath_to_slashpath
from awsfabrictasks.utils import slashpath_to_localpath
from awsfabrictasks.conf import awsfab_settings
from awsfabrictasks.utils import compute_localfile_md5sum


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


def dirlist_absfilenames(dirpath):
    """
    Get all the files within the given ``dirpath`` as a set of absolute
    filenames.
    """
    allfiles = set()
    for root, dirs, files in walk(dirpath):
        abspaths = map(lambda filename: join(root, filename), files)
        allfiles.update(abspaths)
    return allfiles

def s3list_s3filedict(bucket, prefix):
    """
    Get all the keys with the given ``prefix`` as a dict with key-name as key
    and the key-object wrappen in a :class:`S3File` as value.
    """
    result = {}
    for key in bucket.list(prefix=prefix):
        result[key.name] = S3File(bucket, key)
    return result

def localpath_to_s3path(localdir, localpath, s3prefix):
    """
    Convert a local filepath into a S3 path within the given ``s3prefix``.

    :param localdir: The local directory that corresponds to ``s3prefix``.
    :param localpath: Path to a file within ``localdir``.
    :param s3prefix: Prefix to use for the file on S3.

    Example::
    >>> localpath_to_s3path('/mydir', '/mydir/hello/world.txt', 'my/test')
    'my/test/hello/world.txt'
    """
    localdir = force_slashend(localpath_to_slashpath(abspath(localdir)))
    localpath = localpath_to_slashpath(abspath(localpath))
    s3prefix = force_slashend(s3prefix)
    relpath = localpath[len(localdir):]
    return s3prefix + relpath

def s3path_to_localpath(s3prefix, s3path, localdir):
    """
    Convert a s3 filepath into a local filepath within the given ``localdir``.

    :param s3prefix: Prefix used for the file on S3.
    :param s3path: Path to a file within ``s3prefix``.
    :param localdir: The local directory that corresponds to ``s3prefix``.

    Example::
    >>> s3path_to_localpath('mydir/', 'mydir/hello/world.txt', '/my/test')
    '/my/test/hello/world.txt'
    """
    s3prefix = force_slashend(s3prefix)
    localpath = slashpath_to_localpath(s3path[len(s3prefix):])
    return join(localdir, localpath)

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

class S3FileNoInfo(S3FileErrorBase):
    """
    Raised when trying to use :class:`S3File` metadata before performing a HEAD
    request.
    """
    def __str__(self):
        return ('{0}: No info about the key. Use S3File.perform_headrequest(), '
                'or initialize with head=True.').format(super(S3FileNoInfo, self).__str__())


class S3File(object):
    """
    Simplifies working with keys in S3 buckets.
    """

    @classmethod
    def raw(cls, bucket, name):
        key = Key(bucket)
        key.name = name
        return cls(bucket, key)

    @classmethod
    def from_head(cls, bucket, name):
        return cls(bucket, bucket.get_key(name))

    def __init__(self, bucket, key):
        self.bucket = bucket
        self.key = key

    def _overwrite_check(self, overwrite):
        if not overwrite and self.key.exists():
            raise S3FileExistsError(self)

    def _has_info_check(self):
        if self.key.etag == None or self.key.is_latest == None:
            raise S3FileNoInfo(self)

    def get_metadata(self, metadata_name):
        self._has_info_check()
        return self.key.get_metadata(metadata_name)

    def get_checksum(self):
        return self.get_metadata('awsfabchecksum')

    def exists(self):
        """
        Return ``True`` if the key/file exists in the S3 bucket.
        """
        return self.key.exists()

    def get_etag(self):
        """
        Return the etag (the md5sum)
        """
        self._has_info_check()
        return self.key.etag.strip('"')

    def etag_matches_localfile(self, localfile):
        """
        Return ``True`` if the file at the path given in ``localfile`` has an
        md5 hex-digested checksum matching the etag of this S3 key.
        """
        return self.get_etag() == compute_localfile_md5sum(localfile)

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
                                                      bucket=self.bucket,
                                                      name=self.key.name)


class S3SyncIterFile(object):
    """
    Objects of this class is yielded by :meth:`S3Sync.iterfiles`.
    Contains info about where the file exists, its local and S3 path (even if
    it does not exist).
    """
    def __init__(self):
        #: The local path. Always set.
        #: Use :obj:`.localexists` if you want to know if the local file exists.
        self.localpath = None

        #: Local file exists?
        self.localexists = False

        #: The S3 path. Always set.
        #: Use :obj:`.s3exists` if you want to know if the S3 file exists.
        self.s3path = None

        #: A :class:`S3File` object.
        #: Use :obj:`.s3exists` if you want to know if the S3 file exists.
        self.s3file = None

        #: S3 file exists?
        self.s3exists = False

    def __str__(self):
        return ('S3SyncIterFile(localpath={localpath}, '
                'localexists={localexists}, s3path={s3path}, s3file={s3file}, '
                's3exists={s3exists})').format(**self.__dict__)

    def both_exists(self):
        """
        Returns ``True`` if :obj:`.localexists` and :obj:`.s3exists`.
        """
        return self.localexists and self.s3exists

    def etag_matches_localfile(self):
        """
        Shortcut for::

            self.s3file.etag_matches_localfile(self.localpath)
        """
        return self.s3file.etag_matches_localfile(self.localpath)

    def create_localdir(self):
        """
        Create the directory containing :obj:`.localpath` if it does not exist.
        """
        dname = dirname(self.localpath)
        if not exists(dname):
            makedirs(dname)

    def download_s3file_to_localfile(self):
        """
        :meth:`.create_localdir` and download the file at :obj:`.s3path` to
        :obj:`.localpath`.
        """
        self.create_localdir()
        self.s3file.get_contents_to_filename(self.localpath)

class S3Sync(object):
    """
    Makes it easy to sync files to and from S3. This class does not make any
    changes to the local filesyste, or S3, it only makes it easy to write
    function that works with hierarkies of files synced locally and on S3.

    A good example is the sourcecode for :func:`awsfabrictasks.s3.tasks.s3_syncupload_dir`.
    """
    def __init__(self, bucket, local_dir, s3prefix):
        """
        :param bucket: A :class:`boto.rds.bucket.DBInstance` object.
        :param local_dir: The local directory.
        :param local_dir: The S3 key prefix that corresponds to ``local_dir``.
        """
        self.bucket = bucket
        self.local_dir = local_dir
        self.s3prefix = force_slashend(s3prefix)

    def _get_localfiles_set(self):
        return dirlist_absfilenames(self.local_dir)

    def _get_s3filedict(self):
        return s3list_s3filedict(self.bucket, self.s3prefix)

    def iterfiles(self):
        """
        Iterate over all files both local and within the S3 prefix.
        Yields :class:`S3SyncIterFile` objects.

        How it works:

            - Uses :func:`dirlist_absfilenames` to get all local files in the ``local_dir``.
            - Uses :func:`s3list_s3filedict` to get all S3 files in the ``s3prefix``.
            - Uses these two sets of information to create :class:`S3SyncIterFile` objects.
        """
        s3filedict = self._get_s3filedict()
        localfiles_set = self._get_localfiles_set()
        synced_s3paths = set()

        # Handle files that are locally, and possibly also on S3
        for localpath in localfiles_set:
            syncfile = S3SyncIterFile()
            syncfile.localpath = localpath
            syncfile.localexists = True
            syncfile.s3path = localpath_to_s3path(self.local_dir, localpath, self.s3prefix)
            synced_s3paths.add(syncfile.s3path)
            syncfile.s3exists = syncfile.s3path in s3filedict
            if syncfile.s3exists:
                syncfile.s3file = s3filedict[syncfile.s3path]
            else:
                syncfile.s3file = S3File.raw(self.bucket, syncfile.s3path)
            yield syncfile

        # Handle files that are only on S3
        only_remote_keys = set(s3filedict.keys()).difference(synced_s3paths)
        for s3path in only_remote_keys:
            s3file = S3File.raw(self.bucket, s3path)
            syncfile = S3SyncIterFile()
            syncfile.s3path = s3path
            syncfile.s3file = s3filedict[syncfile.s3path]
            syncfile.s3exists = True
            syncfile.localexists = False
            syncfile.localpath = s3path_to_localpath(self.s3prefix, s3path, self.local_dir)
            yield syncfile
