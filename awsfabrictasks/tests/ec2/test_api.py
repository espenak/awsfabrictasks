from unittest import TestCase

from awsfabrictasks.ec2.api import ec2_rsync_download_command
from awsfabrictasks.ec2.api import ec2_rsync_upload_command
from awsfabrictasks.ec2.api import Ec2LaunchInstance
from awsfabrictasks.ec2.api import zipit
from awsfabrictasks.conf import awsfab_settings


class TestRsync(TestCase):
    class MockEc2InstanceWrapper(object):
        def get_ssh_uri(self):
            return 'test@example.com'
        def get_ssh_key_filename(self):
            return '/path/to/key.pem'

    def setUp(self):
        self.instancewrapper = TestRsync.MockEc2InstanceWrapper()
        awsfab_settings.EXTRA_SSH_ARGS = ''

    def test_ec2_rsync_download_command(self):
        self.assertEquals(ec2_rsync_download_command(self.instancewrapper, '/etc', '/tmp/etc'),
                          'rsync -av -e "ssh -i /path/to/key.pem " test@example.com:/etc /tmp/etc')
        self.assertEquals(ec2_rsync_download_command(self.instancewrapper, '/etc/', '/tmp/etc'),
                          'rsync -av -e "ssh -i /path/to/key.pem " test@example.com:/etc /tmp/etc')
        self.assertEquals(ec2_rsync_download_command(self.instancewrapper, '/etc/', '/tmp/etc', sync_content=True),
                          'rsync -av -e "ssh -i /path/to/key.pem " test@example.com:/etc/ /tmp/etc')
        self.assertEquals(ec2_rsync_download_command(self.instancewrapper, '/etc/', '/tmp/etc', sync_content=False),
                          ec2_rsync_download_command(self.instancewrapper, '/etc/', '/tmp/etc'))

    def test_ec2_rsync_download_command_extra_ssh_args(self):
        awsfab_settings.EXTRA_SSH_ARGS = 'TEST'
        self.assertEquals(ec2_rsync_download_command(self.instancewrapper, '/etc/', '/tmp/etc'),
                          'rsync -av -e "ssh -i /path/to/key.pem TEST" test@example.com:/etc /tmp/etc')

    def test_ec2_rsync_upload_command(self):
        self.assertEquals(ec2_rsync_upload_command(self.instancewrapper, '/tmp/etc', '/etc'),
                          'rsync -av -e "ssh -i /path/to/key.pem " /tmp/etc test@example.com:/etc')
        self.assertEquals(ec2_rsync_upload_command(self.instancewrapper, '/tmp/etc/', '/etc'),
                          'rsync -av -e "ssh -i /path/to/key.pem " /tmp/etc test@example.com:/etc')
        self.assertEquals(ec2_rsync_upload_command(self.instancewrapper, '/tmp/etc/', '/etc', sync_content=True),
                          'rsync -av -e "ssh -i /path/to/key.pem " /tmp/etc/ test@example.com:/etc')
        self.assertEquals(ec2_rsync_upload_command(self.instancewrapper, '/tmp/etc/', '/etc', sync_content=False),
                          ec2_rsync_upload_command(self.instancewrapper, '/tmp/etc/', '/etc'))

    def test_ec2_rsync_upload_command_extra_ssh_args(self):
        awsfab_settings.EXTRA_SSH_ARGS = 'TEST'
        self.assertEquals(ec2_rsync_upload_command(self.instancewrapper, '/tmp/etc', '/etc'),
                          'rsync -av -e "ssh -i /path/to/key.pem TEST" /tmp/etc test@example.com:/etc')





class TestEc2LaunchInstance(TestCase):
    class Ec2LaunchInstanceMock(Ec2LaunchInstance):
        def _ask_for_configname(self):
            return 'ASKED'
        def check_if_name_exists(self):
            self.NAME_EXISTS_CHECKED = True


    def setUp(self):
        self.conf = {'instance_type': 't1.micro',
                     'key_name': 'awstestkey',
                     'security_groups': ['testgroup'],
                     'extrastuff': 'test'}


    def _create_launcher(self, settings={}, launcher_kw={}):
        awsfab_settings.reset_settings(**settings)
        launcher = self.Ec2LaunchInstanceMock(**launcher_kw)
        return launcher

    def test_init(self):
        launcher = self._create_launcher(settings={'EC2_LAUNCH_CONFIGS': {'ASKED': self.conf}})
        self.assertEquals(launcher.extra_tags, {})
        self.assertEquals(launcher.configname, 'ASKED')
        self.assertEquals(launcher.configname_help, 'Please select one of the following configurations:')
        self.assertEquals(launcher.conf, self.conf)
        self.assertEquals(launcher.kw, {'instance_type': 't1.micro',
                                        'key_name': 'awstestkey',
                                        'security_groups': ['testgroup']})
        self.assertEquals(launcher.instance, None)
        self.assertEquals(launcher.NAME_EXISTS_CHECKED, True)

    def test_userdata(self):
        self.conf['user_data'] = 'testing'
        launcher = self._create_launcher(settings={'EC2_LAUNCH_CONFIGS': {'ASKED': self.conf}})
        self.assertEquals(launcher.kw['user_data'], zipit('testing'))

    def test_specify_configname(self):
        launcher = self._create_launcher(settings={'EC2_LAUNCH_CONFIGS': {'myconf': self.conf}},
                                         launcher_kw={'configname': 'myconf'})
        self.assertEquals(launcher.configname, 'myconf')
        self.assertEquals(launcher.conf, self.conf)

    def test_get_all_tags_empty(self):
        launcher = self._create_launcher(settings={'EC2_LAUNCH_CONFIGS': {'ASKED': self.conf}})
        self.assertEquals(launcher.get_all_tags(), {})

    def test_get_all_tags_from_conf(self):
        self.conf['tags'] = {'sshuser': 'test'}
        launcher = self._create_launcher(settings={'EC2_LAUNCH_CONFIGS': {'ASKED': self.conf}})
        self.assertEquals(launcher.get_all_tags(), {'sshuser': 'test'})

    def test_get_all_tags_from_conf_and_extra(self):
        self.conf['tags'] = {'sshuser': 'test'}
        launcher = self._create_launcher(settings={'EC2_LAUNCH_CONFIGS': {'ASKED': self.conf}},
                                         launcher_kw={'extra_tags': {'port': '15010'}})
        self.assertEquals(launcher.get_all_tags(), {'sshuser': 'test', 'port': '15010'})
