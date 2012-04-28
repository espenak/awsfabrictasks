import cuisine
from fabric.api import put


def upload_config(local_path, remote_path, **file_attribs):
    put(local_path, remote_path, use_sudo=True)
    cuisine.file_attribs(remote_path, **file_attribs)
