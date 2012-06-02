from unittest import TestCase

from awsfabrictasks.ec2.api import ec2_rsync_download_command
from awsfabrictasks.ec2.api import ec2_rsync_upload_command
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
