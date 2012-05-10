from fabric.api import task, run
from awsfabrictasks.decorators import ec2instance


###########################
# Add some of our own tasks
###########################

@task
def uname():
    """
    Run ``uname -a``
    """
    run('uname -a')


@task
@ec2instance(nametag='tst')
def example_nametag_specific_task():
    """
    Example of using ``@ec2instance``.
    Enables us to run::

        awsfab example_nametag_specific_task``

    and have it automatically use the EC2 instance tagged with ``Name="tst"``.
    """
    run('uname -a')


#####################
# Import awsfab tasks
#####################
from awsfabrictasks.ec2.tasks import *
from awsfabrictasks.regions import *
from awsfabrictasks.conf import *
