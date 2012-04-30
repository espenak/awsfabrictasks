from fabric.api import put, sudo


def upload_config(local_path, remote_path, owner=None, mode=None):
    put(local_path, remote_path, use_sudo=True)
    if owner:
        sudo('chown {owner} {remote_path}'.format(**vars()))
    if mode:
        sudo('chmod {mode} {remote_path}'.format(**vars()))
