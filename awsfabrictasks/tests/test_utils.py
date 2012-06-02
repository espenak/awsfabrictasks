from unittest import TestCase

from awsfabrictasks.utils import force_slashend
from awsfabrictasks.utils import force_noslashend
from awsfabrictasks.utils import rsyncformat_path


class TestUtils(TestCase):
    def test_force_slashend(self):
        self.assertEquals(force_slashend('/path/to/'), '/path/to/')
        self.assertEquals(force_slashend('/path/to'), '/path/to/')

    def test_force_noslashend(self):
        self.assertEquals(force_noslashend('/path/to'), '/path/to')
        self.assertEquals(force_noslashend('/path/to/'), '/path/to')
        self.assertEquals(force_noslashend('/path/to////'), '/path/to')

    def test_rsyncformat_path(self):
        self.assertEquals(rsyncformat_path('/path/to'), '/path/to')
        self.assertEquals(rsyncformat_path('/path/to', sync_content=True), '/path/to/')
        self.assertEquals(rsyncformat_path('/path/to'), rsyncformat_path('/path/to', sync_content=False))
