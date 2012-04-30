from fabric.api import put, env, sudo




def upload_config(local_path, remote_path, owner=None, mode=None):
    put(local_path, remote_path, use_sudo=True)
    if owner:
        sudo('chown {owner} {remote_path}'.format(**vars()))
    if mode:
        sudo('chmod {mode} {remote_path}'.format(**vars()))


def format_keypairs_for_ssh_options():
    """
    Get ssh/rsync formatted ``env.key_filename``. E.g.::

        "-i /path/to/key1.pem -i /path/to/key2.pem"
    """
    return ' '.join(['-i {0}'.format(key) for key in env.key_filename])
