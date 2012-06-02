from unittest import TestCase

from awsfabrictasks.utils import force_slashend
from awsfabrictasks.utils import force_noslashend
from awsfabrictasks.utils import rsyncformat_path
from awsfabrictasks.utils import guess_contenttype


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

    def test_guess_contenttype(self):
        self.assertEquals(guess_contenttype('hello.py'), 'text/x-python')
        self.assertEquals(guess_contenttype('hello.txt'), 'text/plain')
        self.assertEquals(guess_contenttype('hello.json'), 'application/json')
