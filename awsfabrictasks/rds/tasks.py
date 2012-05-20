"""
Tasks for RDS instances.
"""
from fabric.api import task

#from awsfabrictasks.conf import awsfab_settings
from awsfabrictasks.rds.api import print_rds_instance
from .api import RdsInstanceWrapper



__all__ = [
        'rds_print_instance',
        ]


@task
def rds_print_instance(dbinstanceid, full=False):
    """
    Print RDS instance info.

    :param dbinstanceid:
        The id/name of the RDS instance.
    :param full:
        Print all attributes, or just the most useful ones? Defaults to
        ``False``.
    """
    dbinstancewrapper = RdsInstanceWrapper.get_dbinstancewrapper(dbinstanceid)
    print_rds_instance(dbinstancewrapper.dbinstance, full=bool(full), indentspaces=0)
