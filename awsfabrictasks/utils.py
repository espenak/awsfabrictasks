from fabric.api import put, sudo
from os import walk, remove
from os.path import relpath, join
from mimetypes import guess_type
from tempfile import NamedTemporaryFile
from boto.utils import compute_md5
import logging


#: Map of strings to loglevels (for the logging module)
loglevel_stringmap = {'DEBUG': logging.DEBUG,
                      'INFO': logging.INFO,
                      'WARN': logging.WARN,
                      'ERROR': logging.ERROR,
                      'CRITICAL': logging.CRITICAL,
                      'QUIET': logging.CRITICAL}

class InvalidLogLevel(KeyError):
    """
    Raised when :func:`getLoglevelFromString` gets an invalid ``loglevelstring``.
    """

def getLoglevelFromString(loglevelstring):
    """
    Lookup ``loglevelstring`` in :obj:`loglevel_stringmap`.

    :raise InvalidLogLevel: If loglevelstring is not in :obj:`loglevel_stringmap`.
    :return: The loglevel.
    :rtype: int
    """
    try:
        return loglevel_stringmap[loglevelstring]
    except KeyError as e:
        raise InvalidLogLevel('Invalid loglevel: {0}'.format(loglevelstring))

def configureStreamLogger(loggername, level):
    """
    Configure a stdout/stderr logger (logging.StreamHandler) with the given
    ``loggername`` and ``level``. If you are configuring logging for a
    task, use :func:`configureStreamLoggerForTask`.

    This is suitable for log-configuration for a single task, where the user
    specifies a loglevel.

    .. seealso:
        :func:`configureStreamLoggerForTask`,
        :func:`getLoglevelFromString`.

    :return: The configured logger.
    """
    logger = logging.getLogger(loggername)
    logger.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

def configureStreamLoggerForTask(modulename, taskname, loglevel):
    """
    Configure logging for a task.

    Shortcut for::

        configureStreamLogger(modulename + '.' + taskname, loglevel)

    Example (note that what you put in the loglevel docs for your task depends
    on how you use the logger)::

        @task
        mytask(loglevel='INFO'):
            \"\"\"
            Does some task.

            :param loglevel:
                Controls the amount of output:

                    QUIET --- No output.
                    INFO --- Only produce output for changes.
                    DEBUG --- One line of output for each file.

            Defaults to "INFO".
            \"\"\"
            log = configureStreamLoggerForTask(__name__, 's3_syncupload_dir',
                                               getLoglevelFromString(loglevel))
            log.info('Hello world')
    """
    return configureStreamLogger(modulename + '.' + taskname, loglevel)


def sudo_chown(remote_path, owner):
    """
    Run ``sudo chown <owner> remote_path``.
    """
    sudo('chown {owner} {remote_path}'.format(**vars()))

def sudo_chmod(remote_path, mode):
    """
    Run ``sudo chmod <mode> remote_path``.
    """
    sudo('chmod {mode} {remote_path}'.format(**vars()))

def sudo_chattr(remote_path, owner=None, mode=None):
    """
    Run :func:`sudo_chown` and :func:`sudo_chmod` on ``remote_path``.
    If owner or mode is None, their corresponding function is not called.
    """
    if owner:
        sudo_chown(remote_path, owner)
    if mode:
        sudo_chmod(remote_path, mode)

def sudo_upload_file(local_path, remote_path, **chattr_kw):
    """
    Use sudo to upload a file from ``local_path`` to ``remote_path`` and run
    :func:`sudo_chattr` with the given ``chattr_kw`` as arguments.
    """
    put(local_path, remote_path, use_sudo=True)
    sudo_chattr(remote_path, **chattr_kw)

def sudo_upload_string_to_file(string_to_upload, remote_path, **chattr_kw):
    """
    Create a tempfile containing ``string_to_upload``, and use
    :func:`sudo_upload_file` to upload the tempfile. Removes the tempfile
    when the upload is complete or if it fails.

    :param string_to_upload: The string to write to the tempfile.
    :param remote_path: See :func:`sudo_upload_file`.
    :param chattr_kw: See :func:`sudo_upload_file`.
    """
    tmpfile = NamedTemporaryFile(delete=False)
    try:
        tmpfile.write(string_to_upload)
        tmpfile.close()
        sudo_upload_file(tmpfile.name, remote_path, **chattr_kw)
    finally:
        remove(tmpfile.name)


def sudo_mkdir_p(remote_path, **chattr_kw):
    """
    ``sudo mkdir -p <remote_path>`` followed by :func:`sudo_chattr`(remote_path, **chattr_kw).
    """
    sudo('mkdir -p {remote_path}'.format(**vars()))
    sudo_chattr(remote_path, **chattr_kw)


def sudo_upload_dir(local_dir, remote_dir, **chattr_kw):
    """
    Upload all files and directories in ``local_dir`` to ``remote_dir``.
    Directories are created with :func:`sudo_mkdir_p` and files are uploaded
    with :func:`sudo_upload_file`. ``chattr_kw`` is forwarded in both cases.
    """
    for local_dirpath, dirnames, filenames in walk(local_dir):
        remote_dirpath = remote_dir
        rel = relpath(local_dirpath, local_dir)
        if rel != '.':
            remote_dirpath = join(remote_dir, rel)
        #print local_dirpath, '-->', remote_dirpath
        sudo_mkdir_p(remote_dirpath, **chattr_kw)
        for filename in filenames:
            local_filepath = join(local_dirpath, filename)
            remote_filepath = join(remote_dirpath, filename)
            #print local_filepath, '-->', remote_filepath
            sudo_upload_file(local_filepath, remote_filepath, **chattr_kw)


def parse_bool(data):
    """
    Return ``True`` if data is one of:: ``'true', 'True', True``. Otherwise,
    return ``False``.
    """
    return data in ('true', 'True', True)

def force_slashend(path):
    """
    Return ``path`` suffixed with ``/`` (path is unchanged if it is already
    suffixed with ``/``).
    """
    if not path.endswith('/'):
        path = path + '/'
    return path

def force_noslashend(path):
    """
    Return ``path`` with any trailing ``/`` removed.
    """
    if path.endswith('/'):
        path = path.rstrip('/')
    return path

def localpath_to_slashpath(path):
    """
    Replace ``os.sep`` in ``path`` with ``/``.
    """
    from os import sep
    return path.replace(sep, '/')

def slashpath_to_localpath(path):
    """
    Replace ``/`` in ``path`` with ``os.sep`` .
    """
    from os import sep
    return path.replace('/', sep)

def rsyncformat_path(source_dir, sync_content=False):
    """
    rsync uses ``/`` in the source directory to determine if we should
    sync a directory or the contents of a directory. How rsync works:

    Sync contents:
        Source path ending with ``/`` means sync the contents (just as if we
        used ``/*`` except that ``*`` does not include hidden files).
    Sync the directory:
        Source path NOT ending with ``/`` means sync the directory. I.e.: If
        the source is ``/etc/init.d``,  and the destination is ``/tmp``, the contents
        of ``/etc/init.d`` is copied into ``/tmp/init.d/``.

    This is error-prone, and the consequences can be severe if combined with
    ``--delete``. Therefore, we use a boolean to distinguish between these two
    methods of specifying source directory, and reformat the path using
    :func:`force_slashend` and :func:`force_noslashend`.

    :param source_dir:
        The source directory. May be a remote directory (i.e.:
        [USER@]HOSTNAME:PATH), or a local directory.
    :param sync_content: Normally the function automatically makes sure
        ``local_dir`` is not suffixed with ``/``, which makes rsync copy
        ``local_dir`` into ``remote_dir``. With ``sync_content=True``,
        the content of ``local_dir`` is synced into ``remote_dir`` instead.
    """
    if sync_content:
        return force_slashend(source_dir)
    else:
        return force_noslashend(source_dir)

def compute_localfile_md5sum(localfile):
    """
    Compute the hex-digested md5 checksum of the given ``localfile``.

    :param localfile: Path to a file on the local filesystem.
    """
    fp = open(localfile, 'rb')
    md5sum = compute_md5(fp)[0]
    fp.close()
    return md5sum

def guess_contenttype(filename):
    """
    Return the content-type for the given ``filename``. Uses
    :func:`mimetypes.guess_type`.
    """
    return guess_type(filename)[0]
