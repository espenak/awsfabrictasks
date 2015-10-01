from __future__ import print_function

from fabric.api import task
from boto.ec2 import regions, connect_to_region

from .conf import awsfab_settings



@task
def list_regions():
    """
    List all regions.
    """
    for region in regions(**awsfab_settings.AUTH):
        print('- {name} (endpoint: {endpoint})'.format(**region.__dict__))


@task
def list_zones(region=awsfab_settings.DEFAULT_REGION):
    """
    List zones in the given region.

    :param region: Defaults to ``awsfab_settings.DEFAULT_REGION``.
    """
    connection = connect_to_region(region_name=region, **awsfab_settings.AUTH)
    print('Zones in {region}:'.format(region=region))
    for zone in connection.get_all_zones():
        print('- {name} (state:{state})'.format(**zone.__dict__))
