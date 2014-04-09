from fabric.api import local, task


@task
def docs():
    """
    Build the Trafo docs.
    """
    local('sphinx-build -b html docs/ build/docs')
