import cuisine
from fabric.api import put, env


def upload_config(local_path, remote_path, **file_attribs):
    put(local_path, remote_path, use_sudo=True)
    cuisine.file_attribs(remote_path, **file_attribs)


def format_keypairs_for_ssh_options():
    """
    Get ssh/rsync formatted ``env.key_filename``. E.g.::

        "-i /path/to/key1.pem -i /path/to/key2.pem"
    """
    return ' '.join(['-i {0}'.format(key) for key in env.key_filename])
