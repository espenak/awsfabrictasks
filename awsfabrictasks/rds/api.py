from __future__ import print_function

from pprint import pformat
from boto.rds import connect_to_region

from awsfabrictasks.conf import awsfab_settings


class RdsRegionConnectionError(Exception):
    """
    Raised when we fail to connect to a region.
    """
    def __init__(self, region):
        self.region = region
        msg = 'Could not connect to region: {region}'.format(**vars())
        super(RdsRegionConnectionError, self).__init__(msg)


class RdsInstanceWrapper(object):
    """
    .. warning::
        This class is experimental, so we may make backwards-incompatible
        changes to it in the future.
    """
    def __init__(self, dbinstance):
        """
        :param dbinstance: A :class:`boto.rds.dbinstance.DBInstance` object.
        """
        self.dbinstance = dbinstance

    def __str__(self):
        return 'RdsInstanceWrapper:{0}'.format(self.get_id())

    def __repr__(self):
        return 'RdsInstanceWrapper({0})'.format(self.get_id())

    def get_id(self):
        return self.dbinstance.id

    @classmethod
    def get_connection(cls, region=None):
        """
        Connect to the given region, and return the connection.

        :param region:
            Defaults to ``awsfab_settings.DEFAULT_REGION`` if ``None``.
        """
        region = region is None and awsfab_settings.DEFAULT_REGION or region
        connection = connect_to_region(region_name=region, **awsfab_settings.AUTH)
        if not connection:
            raise RdsRegionConnectionError(region)
        return connection

    @classmethod
    def get_all_dbinstancewrappers(cls, region=None):
        """
        Get :class:`RdsInstanceWrapper` wrappers for all RDS dbinstances in the
        given region.

        Uses :meth:`.get_connection` to connect to the region.
        """
        connection = cls.get_connection(region)
        dbinstances = connection.get_all_dbinstances()
        dbinstancewrappers = [cls(dbinstance) for dbinstance in dbinstances]
        return dbinstancewrappers

    @classmethod
    def get_dbinstancewrapper(cls, instanceid, region=None):
        """
        Get an :class:`RdsInstanceWrapper` for the db instance with the given
        ``instanceid``.

        :raise LookupError:
            If the instance is not found.
        """
        for dbinstancewrapper in cls.get_all_dbinstancewrappers(region=region):
            if dbinstancewrapper.get_id() == instanceid:
                return dbinstancewrapper
        raise LookupError('Could not find any RDS dbinstance with id={0}'.format(instanceid))


def print_rds_instance(dbinstance, full=False, indentspaces=0):
    """
    Print attributes of an RDS instance.

    :param dbinstance: A :class:`boto.rds.dbinstance.DBInstance` object.
    :param full: Print all attributes? If not, a subset of the attributes are printed.
    :param indentspaces: Number of spaces to indent each line in the output.
    """
    indent = ' ' * indentspaces
    print('{indent}id={id}:'.format(indent=indent, id=dbinstance.id))
    indent = ' ' * (indentspaces + 3)
    if full:
        attrnames = sorted(dbinstance.__dict__.keys())
    else:
        attrnames = ['status', 'endpoint', 'DBName', 'master_username',
                     'instance_class', 'availability_zone']
    for attrname in attrnames:
        if attrname.startswith('_'):
            continue
        value = dbinstance.__dict__[attrname]
        if not isinstance(value, (str, unicode, bool, int)):
            value = pformat(value)
        print('{indent}{attrname}: {value}'.format(**vars()))
