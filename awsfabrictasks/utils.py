from fabric.api import put, sudo
from os import walk
from os.path import relpath, join


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
