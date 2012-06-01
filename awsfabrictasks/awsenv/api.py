from awsfabrictasks.ec2.api import Ec2InstanceWrapper
from awsfabrictasks.conf import awsfab_settings
from awsfabrictasks.rds.api import RdsInstanceWrapper



class AwsEnvironment(object):
    """
    .. warning::
        This class is experimental, so we may make backwards-incompatible
        changes to it in the future.
    """
    #: The tag used to mark EC2 instances with their environment
    ec2_environment_tag = 'environment'

    def __init__(self, environment, region=None):
        """
        :param environment:
            The name of the environment. See: :meth:`.get_rds_instances`,
            :meth:`.get_ec2_instancewrappers`.
        :param region:
            The region where this environment belongs. Defaults to
            ``awsfab_settings.DEFAULT_REGION``.
        """
        self.environment = environment
        self.region = region or awsfab_settings.DEFAULT_REGION

    def get_rds_instancewrappers(self):
        """
        Get all RDS instances where the ID is prefixed with :obj:`.environment`.
        """
        dbinstancewrappers = RdsInstanceWrapper.get_all_dbinstancewrappers(region=self.region)
        return filter(lambda w: w.get_id().startswith(self.environment), dbinstancewrappers)

    def get_ec2_instancewrappers(self, tags={}):
        alltags = {}
        alltags.update(tags)
        alltags[self.ec2_environment_tag] = self.environment
        instancewrappers = Ec2InstanceWrapper.get_by_tagvalue(tags=alltags, region=self.region)
        return instancewrappers


def create_hostslist_from_environment(environment):
    awsenvironment = AwsEnvironment(environment)
    instancewrappers = awsenvironment.get_ec2_instancewrappers()
