from fabric.api import task, abort
from fabric.contrib.console import confirm
from os import linesep
from os.path import exists, expanduser, abspath

from awsfabrictasks.conf import awsfab_settings
from awsfabrictasks.utils import force_slashend
from awsfabrictasks.utils import parse_bool
from .api import S3ConnectionWrapper
from .api import iter_bucketcontents
from .api import S3File
from .api import S3FileExistsError
from .api import s3list_s3filedict
from .api import dirlist_absfilenames
from .api import localpath_to_s3path


@task
def s3_ls(bucketname, prefix='', search=None, match=None, style='compact',
          delimiter=awsfab_settings.S3_DELIMITER):
    """
    List all items with the given prefix within the given bucket.

    :param bucketname: Name of an S3 bucket.
    :param prefix:
        The prefix to list. Defaults to empty string, which lists
        all items in the root directory.
    :param search:
        Search for keys whose name contains this string.
        Shortcut for ``match="*<search>*"``.
    :param match:
        A Unix shell style pattern to match. Matches against the entire key
        name (in filesystem terms: the absolute path).

        Ignored if ``search`` is provided.  Uses the ``fnmatch`` python module.
        The match is case-sensitive.

        Examples::

            *.jpg
            *2012*example*.log
            icon-*.png

    :param style:
        The style of the output. One of:

            - compact
            - verbose
            - nameonly

    :param delimiter:
        The delimiter to use. Defaults to ``awsfab_settings.S3_DELIMITER``.
    """
    bucket = S3ConnectionWrapper.get_bucket_using_pattern(bucketname)

    styles = ('compact', 'verbose', 'nameonly')
    if not style in styles:
        abort('Invalid style: {0}. Use one of {1}'.format(style, ','.join(styles)))
    if style == 'compact':
        formatstring = '{name:<70} {size:<10} {last_modified:<25} {mode}'
        print formatstring.format(name='NAME', size='SIZE', last_modified='LAST MODIFIED',
                                  mode='MODE')
    elif style == 'verbose':
        formatstring = '{linesep}'.join(('name: {name}',
                                         '    size: {size}',
                                         '    last_modified: {last_modified}',
                                         '    mode: {mode}'))
    elif style == 'nameonly':
        formatstring = '{name}'

    if search:
        match = '*{0}*'.format(search)

    formatter = lambda key: formatstring.format(linesep=linesep, **key.__dict__)
    for line in iter_bucketcontents(bucket, prefix=prefix, match=match,
                                    delimiter=delimiter, formatter=formatter):
        print line

@task
def s3_listbuckets():
    """
    List all S3 buckets.
    """
    connectionwrapper = S3ConnectionWrapper.get_connection()
    for bucket in connectionwrapper.connection.get_all_buckets():
        loggingstatus = bucket.get_logging_status()
        print '{0}:'.format(bucket.name)
        print '   location:', bucket.get_location()
        print '   loggingstatus:'
        print '      enabled:', loggingstatus.target != None
        print '      prefix:', loggingstatus.prefix
        print '      grants:', loggingstatus.grants


@task
def s3_createfile(bucketname, keyname, contents, overwrite=False):
    """
    Create a file with the given keyname and contents.

    :param bucketname: Name of an S3 bucket.
    :param keyname: The key to create/overwrite (In filesystem terms: absolute file path).
    :param contents: The data to put in the bucket.
    :param overwrite: Overwrite if exists? Defaults to ``False``.
    """
    bucket = S3ConnectionWrapper.get_bucket_using_pattern(bucketname)
    s3file = S3File.raw(bucket, keyname)
    try:
        s3file.set_contents_from_string(contents, overwrite)
    except S3FileExistsError, e:
        abort(str(e))


@task
def s3_uploadfile(bucketname, keyname, localfile, overwrite=False):
    """
    Upload a local file.

    :param bucketname: Name of an S3 bucket.
    :param keyname: The key to create/overwrite (In filesystem terms: absolute file path).
    :param localfile: The local file to upload.
    :param overwrite: Overwrite if exists? Defaults to ``False``.
    """
    localfile = expanduser(localfile)
    bucket = S3ConnectionWrapper.get_bucket_using_pattern(bucketname)
    s3file = S3File.raw(bucket, keyname)
    try:
        s3file.set_contents_from_filename(localfile, overwrite)
    except S3FileExistsError, e:
        abort(str(e))

@task
def s3_printfile(bucketname, keyname):
    """
    Print the contents of the given key/file to stdout.

    :param bucketname: Name of an S3 bucket.
    :param keyname: The key to print (In filesystem terms: absolute file path).
    """
    bucket = S3ConnectionWrapper.get_bucket_using_pattern(bucketname)
    s3file = S3File.raw(bucket, keyname)
    print s3file.get_contents_as_string()

@task
def s3_downloadfile(bucketname, keyname, localfile, overwrite=False):
    """
    Print the contents of the given key/file to stdout.

    :param bucketname: Name of an S3 bucket.
    :param keyname: The key to download (In filesystem terms: absolute file path).
    :param localfile: The local file to write the data to.
    :param overwrite: Overwrite local file if exists? Defaults to ``False``.
    """
    localfile = expanduser(localfile)
    if exists(localfile) and not overwrite:
        abort('Local file exists: {0}'.format(localfile))
    bucket = S3ConnectionWrapper.get_bucket_using_pattern(bucketname)
    s3file = S3File.raw(bucket, keyname)
    print s3file.get_contents_to_filename()

@task
def s3_delete(bucketname, keyname, noconfirm=False):
    """
    Remove a "file" from the given bucket.

    :param bucketname: Name of an S3 bucket.
    :param keyname: The key to remove (In filesystem terms: absolute file path).
    :param noconfirm:
        If this is ``True``, we will not ask for confirmation before
        removing the key. Defaults to ``False``.
    """
    bucket = S3ConnectionWrapper.get_bucket_using_pattern(bucketname)
    s3file = S3File.raw(bucket, keyname)
    if not parse_bool(noconfirm):
        if not confirm('Remove {0}?'.format(keyname)):
            abort('Aborted')
    s3file.delete()


@task
def s3_is_same_file(bucketname, keyname, localfile):
    """
    Check if the ``keyname`` in the given ``bucketname`` has the same etag as
    the md5 checksum of the given ``localfile``. Files with the same md5sum are
    extremely likely to have the same contents. Prints ``True`` or ``False``.

    Files matching as the same file by this task is considered the same file by
    :func:`s3_upload_dir`.
    """
    localfile = expanduser(localfile)
    bucket = S3ConnectionWrapper.get_bucket_using_pattern(bucketname)
    s3file = S3File.from_head(bucket, keyname)
    print s3file.etag_matches_localfile(localfile)

@task
def s3_syncupload_dir(bucketname, local_dir, s3_prefix, verbosity=2, delete=False,
                      pretend=False):
    """
    Sync a local directory into a S3 bucket. Uses the same method as the
    :func:`s3_is_same_file` task to determine if a local file differs from a
    file on S3.

    :param bucketname: Name of an S3 bucket.
    :param local_dir: The local directory to sync to S3.
    :param s3_prefix: The S3 prefix to use for the uploaded files.
    :param verbosity:
        Controls the amount of output:

            0 --- No output.
            1 --- Only produce output for changes.
            2 --- One line of output for each file.

        Defaults to 2.
    :param delete:
        Delete remote files that are not present in ``local_dir``.
    :param pretend:
        Do not change anything. With ``verbosity=2``, this gives a good
        overview of the changes applied by running the task.
    """
    verbosity = int(verbosity)
    def verboseprint(level, msg, *args, **kwargs):
        if verbosity >= level:
            print msg.format(*args, **kwargs)

    pretend = parse_bool(pretend)
    s3_prefix = force_slashend(s3_prefix)
    local_dir = abspath(expanduser(local_dir))
    bucket = S3ConnectionWrapper.get_bucket_using_pattern(bucketname)
    s3filedict = s3list_s3filedict(bucket, s3_prefix)
    localfiles_set = dirlist_absfilenames(local_dir)

    synced_s3paths = set()
    for localpath in localfiles_set:
        s3path = localpath_to_s3path(local_dir, localpath, s3_prefix)
        synced_s3paths.add(s3path)
        if s3path in s3filedict:
            s3file = s3filedict[s3path]
            if s3file.etag_matches_localfile(localpath):
                verboseprint(2, 'UNCHANGED {0}', s3path)
            else:
                if not pretend:
                    s3file.set_contents_from_filename(localpath, overwrite=True)
                verboseprint(1, 'UPDATED {0}', s3path)
        else:
            s3file = S3File.raw(bucket, s3path)
            if not pretend:
                s3file.set_contents_from_filename(localpath)
            verboseprint(1, 'CREATED {0}', s3path)

    if parse_bool(delete):
        only_remote_keys = set(s3filedict.keys()).difference(synced_s3paths)
        for keyname in only_remote_keys:
            s3file = S3File.raw(bucket, keyname)
            if not pretend:
                s3file.delete()
            verboseprint(1, 'DELETED {0}', keyname)
