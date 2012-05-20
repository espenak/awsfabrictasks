from awsfabrictasks.utils import sudo_upload_string_to_file

hostsfile_template = """
127.0.0.1 localhost

# The following lines are desirable for IPv6 capable hosts
::1 ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
ff02::3 ip6-allhosts

{custom_hosts}
"""

class Host(object):
    def __init__(self, hostname, ip, suffix=''):
        self.hostname = hostname
        self.ip = ip
        self.suffix = suffix

    def __str__(self):
        return '{ip} {hostname}{suffix}'.format(**self.__dict__)

class HostsList(list):
    def __str__(self):
        return '\n'.join(str(host) for host in self)

def create_hostslist_from_ec2instancewrappers(instancewrappers):
    hostslist = HostsList()
    for instancewrapper in instancewrappers:
        if not instancewrapper.is_running():
            raise ValueError('EC2 instance "{0}" is not RUNNING.'.format(instancewrapper))
        ip = instancewrapper.instance.private_ip_address
        role = instancewrapper.instance.tags['hostname']
        hostslist.append(Host(hostname=role, ip=ip, suffix='.ec2'))
    return hostslist

def create_hostsfile_from_ec2instancewrappers(instancewrappers):
    hostslist = create_hostslist_from_ec2instancewrappers(instancewrappers)
    return hostsfile_template.format(custom_hosts=hostslist)

def upload_hostsfile(hostsfile_string):
    sudo_upload_string_to_file(hostsfile_string, '/etc/hosts')
