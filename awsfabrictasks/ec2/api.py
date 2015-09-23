from __future__ import print_function, unicode_literals

from os.path import exists, join, expanduser, abspath
from warnings import warn
from pprint import pformat
from boto.ec2 import connect_to_region
from fabric.api import local, env, abort

from awsfabrictasks.conf import awsfab_settings
from awsfabrictasks.utils import rsyncformat_path

def zipit(ss):
    """
    Returns a string containing a user_data compatible gzip-file
    of the zipped ss input.
    Note(using zlib alone is not sufficient - we need a zipfile structure)
    """
    try:
        from io import BytesIO as StringIO
    except ImportError:
        from StringIO import StringIO
    import gzip
    out = StringIO()
    f = gzip.GzipFile(fileobj=out, mode='wb')
    f.write(ss.encode('utf-8'))
    f.close()
    return out.getvalue()

def ec2_rsync_upload_command(instancewrapper, local_dir, remote_dir,
                             rsync_args='-av', sync_content=False):
    """
    Returns the rsync command used by :func:`ec2_rsync_upload`. Takes the
    same parameters as :func:`ec2_rsync_upload`, except for the first
    parameter, ``instancewrapper``, which is a :class:`Ec2InstanceWrapper`
    object.
    """
    ssh_uri = instancewrapper.get_ssh_uri()
    key_filename = instancewrapper.get_ssh_key_filename()
    extra_ssh_args = awsfab_settings.EXTRA_SSH_ARGS
    local_dir = rsyncformat_path(local_dir, sync_content)
    rsync_cmd = ('rsync {rsync_args} -e "ssh -i {key_filename} {extra_ssh_args}" '
                 '{local_dir} {ssh_uri}:{remote_dir}').format(**vars())
    return rsync_cmd

def ec2_rsync_upload(local_dir, remote_dir, rsync_args='-av', sync_content=False):
    """
    rsync ``local_dir`` into ``remote_dir`` on the current EC2 instance (the
    one returned by :meth:`Ec2InstanceWrapper.get_from_host_string`).

    :param sync_content: Normally the function automatically makes sure
        ``local_dir`` is not suffixed with ``/``, which makes rsync copy
        ``local_dir`` into ``remote_dir``. With ``sync_content=True``,
        the content of ``local_dir`` is synced into ``remote_dir`` instead.
    """
    instancewrapper = Ec2InstanceWrapper.get_from_host_string()
    rsync_cmd = ec2_rsync_upload_command(instancewrapper, local_dir, remote_dir,
                                         rsync_args, sync_content)
    local(rsync_cmd)

def ec2_rsync(*args, **kwargs):
    """
    .. deprecated:: 1.0.13
        Use :func:`ec2_rsync_upload` instead.
    """
    warn('Deprecated since 1.0.13. Use ec2_rsync_upload instead.', DeprecationWarning)
    return ec2_rsync_upload(*args, **kwargs)

def ec2_rsync_download_command(instancewrapper, remote_dir, local_dir,
                               rsync_args='-av', sync_content=False):
    """
    Returns the rsync command used by :func:`ec2_rsync_download`. Takes the
    same parameters as :func:`ec2_rsync_download`, except for the first
    parameter, ``instancewrapper``, which is a :class:`Ec2InstanceWrapper`
    object.
    """
    ssh_uri = instancewrapper.get_ssh_uri()
    key_filename = instancewrapper.get_ssh_key_filename()
    extra_ssh_args = awsfab_settings.EXTRA_SSH_ARGS
    remote_dir = rsyncformat_path(remote_dir, sync_content)
    rsync_cmd = ('rsync {rsync_args} -e "ssh -i {key_filename} {extra_ssh_args}" '
                 '{ssh_uri}:{remote_dir} {local_dir}').format(**vars())
    return rsync_cmd

def ec2_rsync_download(remote_dir, local_dir, rsync_args='-av', sync_content=False):
    """
    rsync ``remote_dir`` on the current EC2 instance (the
    one returned by :meth:`Ec2InstanceWrapper.get_from_host_string`) into
    ``local_dir``.

    :param sync_content: Normally the function automatically makes sure
        ``local_dir`` is not suffixed with ``/``, which makes rsync copy
        ``local_dir`` into ``remote_dir``. With ``sync_content=True``,
        the content of ``local_dir`` is synced into ``remote_dir`` instead.
    """
    instance = Ec2InstanceWrapper.get_from_host_string()
    rsync_cmd = ec2_rsync_download_command(instance, remote_dir, local_dir,
                                           rsync_args, sync_content)
    local(rsync_cmd)


def _parse_instanceident(instanceid_with_optional_region):
    if ':' in instanceid_with_optional_region:
        region, instanceid = instanceid_with_optional_region.split(':', 1)
    else:
        instanceid = instanceid_with_optional_region
        region = awsfab_settings.DEFAULT_REGION
    return region, instanceid


def parse_instanceid(instanceid_with_optional_region):
    """
    Parse instance id with an optional region-name prefixed. Region name
    is specified by prefixing the instanceid with ``<regionname>:``.

    :return: (region, instanceid) where region defaults to
        ``awsfab_settings.DEFAULT_REGION`` if not prefixed to the id.
    """
    return _parse_instanceident(instanceid_with_optional_region)

def parse_instancename(instancename_with_optional_region):
    """
    Just like :func:`parse_instanceid`, however this is for instance names.
    We keep them as separate functions in case they diverge in the future.

    :return: (region, instanceid) where region defaults to
        ``awsfab_settings.DEFAULT_REGION`` if not prefixed to the name.
    """
    return _parse_instanceident(instancename_with_optional_region)


class Ec2RegionConnectionError(Exception):
    """
    Raised when we fail to connect to a region.
    """
    def __init__(self, region):
        self.region = region
        msg = 'Could not connect to region: {region}'.format(**vars())
        super(Ec2RegionConnectionError, self).__init__(msg)


class InstanceLookupError(LookupError):
    """
    Base class for instance lookup errors.
    """

class MultipleInstancesWithSameNameError(InstanceLookupError):
    """
    Raised when multiple instances with the same nametag is discovered.
    (see: :meth:`Ec2InstanceWrapper.get_by_nametag`)
    """

class NoInstanceWithNameFound(InstanceLookupError):
    """
    Raised when no instace with the requested name is found in
    :meth:`Ec2InstanceWrapper.get_by_nametag`.
    """

class NotExactlyOneInstanceError(InstanceLookupError):
    """
    Raised when more than one instance is found when expecting exactly one instance.
    """

class Ec2InstanceWrapper(object):
    """
    Wraps a :class:`boto.ec2.instance.Instance` with convenience functions.

    :ivar instance: The :class:`boto.ec2.instance.Instance`.
    """
    def __init__(self, instance):
        """
        :param instance: A :class:`boto.ec2.instance.Instance` object.
        """
        self.instance = instance

    def __getitem__(self, key):
        """
        Provides easy access to attributes in ``self.instance``.
        """
        return getattr(self.instance, key)

    def __str__(self):
        return 'Ec2InstanceWrapper:{0}'.format(self.prettyname())

    def __repr__(self):
        return 'Ec2InstanceWrapper({0})'.format(self.prettyname())

    def is_running(self):
        """
        Return ``True`` if state=='running'.
        """
        return self.instance.state == 'running'

    def is_stopped(self):
        """
        Return ``True`` if state=='stopped'.
        """
        return self.instance.state == 'stopped'

    def prettyname(self):
        """
        Return a pretty-formatted name for this instance, using the Name-tag if
        the instance is tagged with it.
        """
        instanceid = self.instance.id
        name = self.instance.tags.get('Name')
        if name:
            return '{instanceid} (name={name})'.format(**vars())
        else:
            return instanceid

    def get_ssh_uri(self):
        """
        Get the SSH URI for the instance.

        :return: "<instance.tags['awsfab-ssh-user']>@<instance.public_dns_name>"
        """
        user = self['tags'].get('awsfab-ssh-user', awsfab_settings.EC2_INSTANCE_DEFAULT_SSHUSER)
        host = self['public_dns_name']
        return '{user}@{host}'.format(**vars())

    def get_ssh_key_filename(self):
        """
        Get the SSH indentify filename (.pem-file) for the instance. Searches
        ``awsfab_settings.KEYPAIR_PATH`` for ``"<instance.key_name>.pem"``.

        :raise LookupError: If the key is not found.
        """
        path = awsfab_settings.KEYPAIR_PATH
        key_name = self.instance.key_name + '.pem'
        for dirpath in path:
            filename = abspath(join(expanduser(dirpath), key_name))
            if exists(filename):
                return filename
        raise LookupError('Could not find {key_name} in awsfab_settings.KEYPAIR_PATH: {path!r}'.format(**vars()))

    def add_instance_to_env(self):
        """
        Add ``self`` to ``fabric.api.env.ec2instances[self.get_ssh_uri()]``,
        and register the key-pair for the instance in
        ``fabric.api.env.key_filename``.
        """
        if not 'ec2instances' in env:
            env['ec2instances'] = {}
        env['ec2instances'][self.get_ssh_uri()] = self
        if not env.key_filename:
            env.key_filename = []
        key_filename = self.get_ssh_key_filename()
        if not key_filename in env.key_filename:
            env.key_filename.append(key_filename)

    @classmethod
    def get_by_nametag(cls, instancename_with_optional_region):
        """
        Connect to AWS and get the EC2 instance with the given Name-tag.

        :param instancename_with_optional_region:
            Parsed with :func:`parse_instancename` to find the region and name.
        :raise Ec2RegionConnectionError: If connecting to the region fails.
        :raise InstanceLookupError:
            Or one of its subclasses if the requested instance was not found in
            the region.
        :return: A :class:`Ec2InstanceWrapper` contaning the requested instance.
        """
        region, name = parse_instancename(instancename_with_optional_region)
        connection = connect_to_region(region_name=region, **awsfab_settings.AUTH)
        if not connection:
            raise Ec2RegionConnectionError(region)
        reservations = connection.get_all_instances(filters={'tag:Name': name})
        if len(reservations) == 0:
            raise NoInstanceWithNameFound('No ec2 instances with tag:Name={0}'.format(name))
        if len(reservations) > 1:
            raise MultipleInstancesWithSameNameError('More than one ec2 reservations with tag:Name={0}'.format(name))
        reservation = reservations[0]
        if len(reservation.instances) != 1:
            raise NotExactlyOneInstanceError('Did not get exactly one instance with tag:Name={0}'.format(name))
        return cls(reservation.instances[0])

    @classmethod
    def get_by_tagvalue(cls, tags={}, region=None):
        """
        Connect to AWS and get the EC2 instance with the given tag:value pairs.

        :param tags
            A string like 'role=testing,fake=yes' to AND a set of ec2
            instance tags
        :param region:
            optional.
        :raise Ec2RegionConnectionError: If connecting to the region fails.
        :return: A list of :class:`Ec2InstanceWrapper`s containing the
            matching instances.
        """

        region = region is None and awsfab_settings.DEFAULT_REGION or region
        connection = connect_to_region(region_name=region, **awsfab_settings.AUTH)
        if not connection:
            raise Ec2RegionConnectionError(region)
        tags = dict((('tag:%s' % oldk, v) for (oldk, v) in tags.items()))
        reservations = connection.get_all_instances(filters=tags)
        if len(reservations) == 0:
            return []

        insts = []
        for r in reservations:
            for instance in r.instances:
                insts.append(cls(instance))
        return insts


    @classmethod
    def get_exactly_one_by_tagvalue(cls, tags, region=None):
        """
        Use :meth:`.get_by_tagvalue` to find instances by ``tags``, but
        raise ``LookupError`` if not exactly one instance is found.
        """
        instances = cls.get_by_tagvalue(tags, region)
        if not len(instances) == 1:
            raise LookupError('Got more than one instance matching {0!r} in region={1!r}'.format(tags, region))
        return instances[0]


    @classmethod
    def get_by_instanceid(cls, instanceid):
        """
        Connect to AWS and get the EC2 instance with the given instance ID.

        :param instanceid_with_optional_region:
            Parsed with :func:`parse_instanceid` to find the region and name.
        :raise Ec2RegionConnectionError: If connecting to the region fails.
        :raise LookupError: If the requested instance was not found in the region.
        :return: A :class:`Ec2InstanceWrapper` contaning the requested instance.
        """
        region, instanceid = parse_instanceid(instanceid)
        connection = connect_to_region(region_name=region, **awsfab_settings.AUTH)
        if not connection:
            raise Ec2RegionConnectionError(region)
        reservations = connection.get_all_instances([instanceid])
        if len(reservations) == 0:
            raise LookupError('No ec2 instances with instanceid={0}'.format(instanceid))
        reservation = reservations[0]
        if len(reservation.instances) != 1:
            raise LookupError('Did not get exactly one instance with instanceid={0}'.format(instanceid))
        return cls(reservation.instances[0])

    @classmethod
    def get_from_host_string(cls):
        """
        If an instance has been registered in ``fabric.api.env`` using
        :meth:`add_instance_to_env`, this method can be used to get
        the instance identified by ``fabric.api.env.host_string``.
        """
        return env.ec2instances[env.host_string]



class WaitForStateError(Exception):
    """
    Raises when :func:`wait_for_state` times out.
    """


def wait_for_state(instanceid, state_name, sleep_intervals=[15, 5], last_sleep_repeat=40):
    """
    Poll the instance with ``instanceid`` until its ``state_name`` matches the
    desired ``state_name``.

    The first poll is performed without any delay, and the rest of the polls are
    performed according to ``sleep_intervals``.

    :param instanceid: ID of an instance.
    :param state_name: The state_name to wait for.
    :param sleep_intervals: List of seconds to wait between each poll for state. The first poll
        is made immediately, then we wait for sleep_intervals[0] seconds before the next poll,
        and repeat for each item in sleep_intervals. Then we repeat for ``last_sleep_repeat``
        using the last item in ``sleep_intervals`` as the timout for each wait.
    :param last_sleep_repeat:
        Number of times to repeat the last item in ``sleep_intervals``. If this
        is 20, we will wait for a maximum of ``sum(sleep_intervals) + sleep_intervals[-1]*20``.
    """
    from time import sleep
    region, instanceid = parse_instanceid(instanceid)
    sleep_intervals.extend([sleep_intervals[-1] for x in xrange(last_sleep_repeat)])
    max_wait_sec = sum(sleep_intervals)
    print('Waiting for {instanceid} to change state to: "{state_name}". Will try for {max_wait_sec}s.'.format(**vars()))

    sleep_intervals_len = len(sleep_intervals)
    for index, sleep_sec in enumerate(sleep_intervals):
        instancewrapper = Ec2InstanceWrapper.get_by_instanceid(instanceid)
        current_state_name = instancewrapper['state']
        if current_state_name == state_name:
            print('.. OK')
            return
        index_n1 = index + 1
        print('.. Current state: "{current_state_name}". Next poll ({index_n1}/{sleep_intervals_len}) for "{state_name}"-state in {sleep_sec}s.'.format(**vars()))
        sleep(sleep_sec)
    raise WaitForStateError('Desired state, "{state_name}", not achieved in {max_wait_sec}s.'.format(**vars()))


def wait_for_stopped_state(instanceid, **kwargs):
    """
    Shortcut for ``wait_for_state(instanceid, 'stopped', **kwargs)``.
    """
    wait_for_state(instanceid, 'stopped', **kwargs)

def wait_for_running_state(instanceid, **kwargs):
    """
    Shortcut for ``wait_for_state(instanceid, 'running', **kwargs)``.
    """
    wait_for_state(instanceid, 'running', **kwargs)


def print_ec2_instance(instance, full=False, indentspaces=3):
    """
    Print attributes of an ec2 instance.

    :param instance: A :class:`boto.ec2.instance.Instance` object.
    :param full: Print all attributes? If not, a subset of the attributes are printed.
    :param indentspaces: Number of spaces to indent each line in the output.
    """
    indent = ' ' * indentspaces
    if full:
        attrnames = sorted(instance.__dict__.keys())
    else:
        attrnames = ['state', 'instance_type', 'ip_address', 'public_dns_name',
                     'private_dns_name', 'private_ip_address',
                     'key_name', 'tags', 'placement']
    for attrname in attrnames:
        if attrname.startswith('_'):
            continue
        try:
            value = instance.__dict__[attrname]
        except KeyError:
            try:
                # Simple backward compatible workaround to boto 2.6.0 attr
                # changes with _state and _placement
                value = instance.__dict__['_' + attrname]
            except KeyError:
                value = '**key "{k}" and "_{k}" missing**'.format(k=attrname)
        if not isinstance(value, (str, bool, int)):
            try:
                if isinstance(value, unicode):
                    break
            except:
                pass
            value = pformat(value, indent=indentspaces+3)
        print('{indent}{attrname}: {value}'.format(**vars()))



class Ec2LaunchInstance(object):
    """
    Launch instances configured in ``awsfab_settings.EC2_LAUNCH_CONFIGS``.

    Example::

        launcher = Ec2LaunchInstance(extra_tags={'Name': 'mytest'})
        launcher.confirm()
        instance = launcher.run_instance()

    Note that this class is optimized for the following use case:

        - Create one or more instances (initialize one or more Ec2LaunchInstance).
        - Confirm using :meth:`.confirm` or :meth:`.confirm_many`.
        - Launch each instance using meth:`Ec2LaunchInstance.run_instance` or :meth:`Ec2LaunchInstance.run_many_instances`.
        - Use :meth:`Ec2LaunchInstance.wait_for_running_state_many` to wait for all instances to launch.
        - Do something with the running instances.

    Example of launching many instances::

        a = Ec2LaunchInstance(extra_tags={'Name': 'a'})
        b = Ec2LaunchInstance(extra_tags={'Name': 'b'})
        Ec2LaunchInstance.confirm_many([a, b])
        Ec2LaunchInstance.run_many_instances([a, b])
        # Note: that we can start doing stuff with ``a`` and ``b`` that does not
        # require the instances to be running, such as setting tags.
        Ec2LaunchInstance.wait_for_running_state_many([a, b])
    """

    #: Number of seconds to sleep before retrying when adding tags gets EC2ResponseError.
    tag_retry_sleep = 2

    #: Number of times to retry when adding tags gets EC2ResponseError.
    tag_retry_count = 4

    @classmethod
    def wait_for_running_state_many(cls, launchers, **kwargs):
        """
        Loop through ``launchers`` and run :func:`wait_for_running_state`.

        :param launchers:
            List of Ec2LaunchInstance objects that have been lauched with
            :meth:`Ec2LaunchInstance.run_instance`.
        :param kwargs:
            Forwarded to :func:`wait_for_running_state`.
        """
        for launcher in launchers:
            wait_for_running_state(launcher.instance.id, **kwargs)

    @classmethod
    def run_many_instances(cls, launchers):
        """
        Loop through ``launchers`` and run :func:`run_instance`.

        :param launchers:
            List of Ec2LaunchInstance objects.
        :param kwargs:
            Forwarded to :func:`wait_for_running_state`.
        """
        for launcher in launchers:
            launcher.run_instance()

    @classmethod
    def confirm_many(cls, launchers):
        """
        Loop through
        Use :meth:`prettyprint` to show the user their choices, and ask
        for confirmation. Runs ``fabric.api.abort()`` if the user does
        not confirm the choices.
        """
        from textwrap import fill
        print(fill('Are you sure you want to launch (create) the following new instances '
                   'with the following settings and tags?', 80))
        print('-' * 80)
        for launcher in launchers:
            print()
            print(launcher.prettyformat())
        print('-' * 80)
        Ec2LaunchInstance._confirm('Create instances')

    @staticmethod
    def _confirm(question):
        if raw_input(question + ' [y/N]? ').lower() != 'y':
            abort('Aborted')

    def __init__(self, extra_tags={}, configname=None,
                 configname_help='Please select one of the following configurations:',
                 duplicate_name_protection=True):
        """
        Initialize the launcher. Runs :meth:`create_config_ask_if_none`.

        :param configname:
            Name of a configuration in
            ``awsfab_settings.EC2_LAUNCH_CONFIGS``.
            If it is ``None``, we ask the user for the configfile.
        :param configname_help:
            The help to show above the prompt for configname input (only used
            if ``configname`` is ``None``.
        """
        if not awsfab_settings.EC2_LAUNCH_CONFIGS:
            abort('You have no awsfab_settings.EC2_LAUNCH_CONFIGS.')
        self.extra_tags = extra_tags

        #: A config dict from awsfab_settings.EC2_LAUNCH_CONFIGS.
        self.conf = {}

        #: Keyword arguments for ``run_instances()``.
        self.kw = {}

        #: See the docs for the __init__ parameter.
        self.configname = configname

        #: See the docs for the __init__ parameter.
        self.configname_help = configname_help

        #: The instance launced by :meth:`.run_instance`. None when
        #: run_instance() has not been invoked.
        self.instance = None

        self.create_config_ask_if_none()
        if duplicate_name_protection:
            self.check_if_name_exists()

    def _ask_for_configname(self):
        """
        Ask the user for a configname.

        :return: The user-provided configname.
        """
        print(self.configname_help)
        print('-' * 80)
        fmt = '{0:>30} | {1}'
        print(fmt.format('NAME', 'DESCRIPTION'))
        for configname, config in awsfab_settings.EC2_LAUNCH_CONFIGS.items():
            description = config.get('description', '')
            print(fmt.format(configname, description))
        print('-' * 80)
        configname = raw_input('Type name of config: ').strip()
        return configname

    def _configure(self, configname):
        if not configname in awsfab_settings.EC2_LAUNCH_CONFIGS:
            abort('"{configname}" is not in awsfab_settings.EC2_LAUNCH_CONFIGS'.format(**vars()))
        conf = awsfab_settings.EC2_LAUNCH_CONFIGS[configname]
        kw = dict(key_name = conf['key_name'],
                  instance_type = conf['instance_type'],
                  security_groups = conf['security_groups'])
        try:
            user_data = zipit(conf['user_data'])
            kw['user_data'] = user_data
        except KeyError:
            pass
        if 'availability_zone' in conf:
            kw['placement'] = conf['region'] + conf['availability_zone']
        self.conf = conf
        self.kw = kw

    def check_if_name_exists(self):
        import sys
        name = self.get_all_tags().get('Name')
        if name:
            print()
            sys.stdout.write('Making sure no EC2 instance with Name={0} exists...'.format(name))
            sys.stdout.flush()
            try:
                wrapper = Ec2InstanceWrapper.get_by_nametag(name)
            except NoInstanceWithNameFound:
                pass
            else:
                abort('An instance named {name} already exists.'.format(name=name))
            print('OK')
            print()

    def create_config_ask_if_none(self):
        """
        Set :obj:`.kw` and :obj:`.conf` using :obj:`configname`.
        Prompt the user for a configname if bool(:obj:`.configname`) is
        ``False``.
        """
        if not self.configname:
            self.configname = self._ask_for_configname()
        self._configure(self.configname)

    def get_all_tags(self):
        """
        Merge tags from the awsfab_settings.EC2_LAUNCH_CONFIGS config, and the
        ``extra_tags`` parameter for __init__, and return the resulting dict.
        """
        tags = {}
        if 'tags' in self.conf:
            tags.update(self.conf['tags'])
        if self.extra_tags:
            tags.update(self.extra_tags)
        return tags

    def prettyformat(self):
        """
        Prettyformat the configuration.
        """
        from os import linesep
        tags = self.get_all_tags()
        stripped = self.kw.copy()
        try:
            del stripped['user_data']
            stripped['user_data'] = "YES!"
        except KeyError:
            pass
        info = '{kw}{linesep}Tags: {tags}'.format(kw=pformat(stripped),
                                                  linesep=linesep,
                                                  tags=pformat(tags))
        if 'Name' in tags:
            name = tags['Name']
            info = 'Name={name}:{linesep}{info}'.format(**vars())
            info = '\n   '.join(info.splitlines())
        return info

    def confirm(self):
        """
        Use :meth:`prettyprint` to show the user their choices, and ask
        for confirmation. Runs ``fabric.api.abort()`` if the user does
        not confirm the choices.
        """
        from textwrap import fill
        print(fill('Are you sure you want to launch (create) a new instance '
                   'with the following settings and tags?', 80))
        print('-' * 80)
        print(self.prettyformat())
        print('-' * 80)
        Ec2LaunchInstance._confirm('Create instance')

    def run_instance(self):
        """
        Run/launch the configured instance, and add the tags to the instance
        (:meth:`.get_all_tags`).

        :return: The launched instance.
        """
        connection = connect_to_region(region_name=self.conf['region'], **awsfab_settings.AUTH)
        reservation = connection.run_instances(self.conf['ami'], **self.kw)
        instance = reservation.instances[0]
        self._add_tags(instance)
        self.instance = instance
        return instance

    def _add_tag(self, instance, tagname, value, retries=0):
        import time
        from boto.exception import EC2ResponseError
        try:
            instance.add_tag(tagname, value)
        except EC2ResponseError:
            if retries > self.tag_retry_count:
                raise
            print(('Got EC2ResponseError while adding tag to {id}. Retrying in '
                   '{sec} seconds...').format(id=instance.id, sec=self.tag_retry_sleep))
            time.sleep(self.tag_retry_sleep)
            self._add_tag(instance, tagname, value, retries=retries+1)

    def _add_tags(self, instance):
        for tagname, value in self.get_all_tags().items():
            self._add_tag(instance, tagname, value)
