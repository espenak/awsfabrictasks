"""
General tasks for AWS management.
"""
from os.path import exists
from fabric.api import task, abort, local, env
from pprint import pformat
from os import mkdir
from boto.ec2 import connect_to_region
from pprint import pprint
import pickle

from conf import awsfab_settings


class Ec2CacheItem(dict):
    def __init__(self, instance):
        for attrname in dir(instance):
            if attrname.startswith('_'):
                continue
            value = getattr(instance, attrname)
            if value == None or isinstance(value, (str, unicode, int)):
                self[attrname] = value
        self['tags'] = instance.tags
        self['region'] = instance.region.name

    def get_ssh_uri(self):
        user = self['tags'].get('awsfab_ssh_user', awsfab_settings.EC2_INSTANCE_DEFAULT_SSHUSER)
        host = self['public_dns_name']
        return '{user}@{host}'.format(**vars())



class Ec2Cache(object):
    def __init__(self):
        self.by_id= {}
        self.by_name = {}
        self._loaded = False

    def _populate(self, region):
        conn = connect_to_region(region_name=region, **awsfab_settings.AUTH)
        for reservation in conn.get_all_instances():
            for instance in reservation.instances:
                cacheitem = Ec2CacheItem(instance)
                self.by_id[instance.id] = cacheitem
                if 'Name' in instance.tags:
                    name = instance.tags['Name']
                    if name in self.by_name:
                        raise ValueError(
                                'Duplicate ``Name`` tag: {0} (used in both: {1} and {2})'.format(
                                    name, instance.id, self.by_name[name]['id']))
                    self.by_name[name] = cacheitem


    def sync(self):
        for region in awsfab_settings.EC2_REGIONS:
            self._populate(region)
        self._loaded = True

    def _load_if_not_loaded(self):
        if self._loaded:
            return
        if awsfab_settings.EC2_CACHE_FILE:
            self.load_from_file()
        else:
            self.sync()

    def get_by_nametag(self, name):
        self._load_if_not_loaded()
        return self.by_name[name]

    def get_by_instanceid(self, instanceid):
        self._load_if_not_loaded()
        return self.by_name[instanceid]

    def as_dict(self):
        self._load_if_not_loaded()
        return dict(by_id=self.by_id, by_name=self.by_name)

    def _save(self):
        f = open(awsfab_settings.EC2_CACHE_FILE, 'wb')
        pickle.dump(self.as_dict(), f)
        f.close()

    def save_if_enabled(self):
        if awsfab_settings.EC2_CACHE_FILE:
            self._save()

    def load_from_file(self):
        if not exists(awsfab_settings.EC2_CACHE_FILE):
            abort('awsfab_settings.EC2_CACHE_FILE "{0}" does not exist. Please '
                  'run the ``ec2_cache`` task to create the cache.'.format(awsfab_settings.EC2_CACHE_FILE))
        f = open(awsfab_settings.EC2_CACHE_FILE, 'rb')
        obj = pickle.load(f)
        f.close()
        self.by_id = obj['by_id']
        self.by_name = obj['by_name']
        self._loaded = True

cache = Ec2Cache()


def get_ec2instance_uri(conf):
    ssh_user = conf.get('ssh_user', 'root')
    public_dns = conf['public_dns']
    return '{ssh_user}@{public_dns}'.format(**vars())

def prompt_for_ec2instancename():
    print 'Please select an EC2 instance (from awsfab_settings.EC2_INSTANCES):'
    for name in awsfab_settings.EC2_INSTANCES:
        print '-', name
    default = awsfab_settings.EC2_DEFAULT_INSTANCE
    name = raw_input('Enter name [{0}]: '.format(default)).strip() or default
    if not name:
        abort('Name is required.')
    return name

def get_ec2instanceconf(name):
    try:
        return awsfab_settings.EC2_INSTANCES[name]
    except KeyError:
        abort('"{name}" not in awsfab_settings.EC2_INSTANCES.'.format(name=name))



def _get_name_from_id(instanceid):
    for name, conf in awsfab_settings.EC2_INSTANCES.iteritems():
        current_id = conf['id']
        if current_id == instanceid:
            return name
    return None

def _print_instance(instance, attrnames=None, indentspaces=3):
    indent = ' ' * indentspaces
    if not attrnames:
        attrnames = sorted(instance.__dict__.keys())
    print '{indent}Key in awsfab_settings.EC2_INSTANCES: {name}'.format(indent=indent, name=_get_name_from_id(instance.id))
    for attrname in attrnames:
        if attrname.startswith('_'):
            continue
        value = instance.__dict__[attrname]
        if not isinstance(value, (str, unicode, bool, int)):
            value = pformat(value)
        print '{indent}{attrname}: {value}'.format(**vars())


@task
def ec2_cache():
    """
    Query AWS for all our EC2 instances and cache the results.
    """
    cache.sync()
    cache.save_if_enabled()


@task
def ec2_print_cache():
    """
    Pretty-print the ec2 cache created with ``ec2_cache``.
    """
    pprint(cache.as_dict())


@task
def ec2_launch_instance(configname):
    """
    Launch new EC2 instance.

    ``ec2_launch_instance:<configname>``, where ``configname`` is a key in
    ``awsfab_settings.EC2_LAUNCH_CONFIGS``.
    """
    conf = awsfab_settings.EC2_LAUNCH_CONFIGS[configname]
    connection = connect_to_region(region_name=conf['region'], **awsfab_settings.AUTH)
    ami_image_id = conf['ami']
    key_pair_name = conf['key_name']
    connection.run_instances(conf['ami'],
                             key_name=conf['key_name'],
                             instance_type=conf['instance_type'],
                             security_groups=conf['security_groups'])

def _ec2_start_instance_by_id(instanceid, region=awsfab_settings.DEFAULT_REGION):
    conn = connect_to_region(region_name=region, **awsfab_settings.AUTH)
    instances_started = conn.start_instances([instanceid])
    for instance in instances_started:
        print 'Started:', instance

def _ec2_stop_instance_by_id(instanceid, region=awsfab_settings.DEFAULT_REGION):
    conn = connect_to_region(region_name=region, **awsfab_settings.AUTH)
    instances_started = conn.stop_instances([instanceid])
    for instance in instances_started:
        print 'Stopped:', instance

@task
def ec2_start_instance(instancename=None):
    if not instancename:
        instancename = prompt_for_ec2instancename()
    conf = get_ec2instanceconf(instancename)
    _ec2_start_instance_by_id(conf['id'], region=conf['region'])

@task
def ec2_stop_instance(instancename=None):
    if not instancename:
        instancename = prompt_for_ec2instancename()
    conf = get_ec2instanceconf(instancename)
    _ec2_stop_instance_by_id(conf['id'], region=conf['region'])

@task
def ec2_list_instances(full=False, region=awsfab_settings.DEFAULT_REGION):
    """
    List EC2 instances in a region. Use ``list_instances:full=true`` for more details.
    """
    conn = connect_to_region(region_name=region, **awsfab_settings.AUTH)

    for reservation in conn.get_all_instances():
        print
        print 'id:', reservation.id
        print '   owner_id:', reservation.owner_id
        print '   groups:'
        for group in reservation.groups:
            print '      - {name} (id:{id})'.format(**group.__dict__)
        print '   instances:'
        for instance in reservation.instances:
            attrnames = None
            if not full:
                attrnames = ['id', 'state', 'instance_type', 'ip_address',
                             'dns_name', 'key_name', 'tags', 'placement']
            _print_instance(instance, attrnames=attrnames, indentspaces=6)



#def parse_ec2hosts():
    #def splitnames(names):
        #return names.split(',')
    #ids = splitnames(env.ec2id)
    #names = splitnames(env.ec2name)
    #for instanceid in 

#def get_single_ec2name():



@task
def ec2_login(instancename=None):
    """
    ``ec2_login:instancename``. Use ssh to log into the given ``instancename``
    using the public_dns, key_name and ssh_user configured for the instance.
    """
    print env.host_string
    print env.key_filename
    #if not instancename:
        #instancename = prompt_for_ec2instancename()
    #conf = get_ec2instanceconf(instancename)
    #key_filenames = awsfab_settings.get_key_filenames(conf['key_name'])
    #options = ['-i {0}'.format(filename) for filename in key_filenames]
    #cmd = ' '.join(['ssh'] + options + [get_ec2instance_uri(conf)])
    #local(cmd)


def register_ec2instances_as_roles():
    for instancename in awsfab_settings.EC2_INSTANCES:
        conf = get_ec2instanceconf(instancename)
        key_name = conf['key_name']
        key_filenames = awsfab_settings.get_key_filenames(key_name)
        ssh_uri = get_ec2instance_uri(conf)
        env.roledefs[instancename] = [ssh_uri]

def register_ec2instances_as_keys():
    env.key_filename = []
    for instancename in awsfab_settings.EC2_INSTANCES:
        conf = get_ec2instanceconf(instancename)
        key_name = conf['key_name']
        key_filenames = awsfab_settings.get_key_filenames(key_name)
        env.key_filename += key_filenames
