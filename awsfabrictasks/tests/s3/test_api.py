from __future__ import unicode_literals

from unittest import TestCase
from shutil import rmtree
from tempfile import mkdtemp
from os import makedirs
from os.path import join, exists, dirname

from awsfabrictasks.s3.api import dirlist_absfilenames
from awsfabrictasks.s3.api import localpath_to_s3path
from awsfabrictasks.s3.api import s3path_to_localpath

def makefile(tempdir, path, contents):
    path = join(tempdir, *path.split('/'))
    if not exists(dirname(path)):
        makedirs(dirname(path))
    open(path, 'wb').write(contents.encode('utf-8'))
    return path


class TestDirlistAbsfilenames(TestCase):
    def setUp(self):
        self.tempdir = mkdtemp()
        files = (('hello/world.txt', 'Hello world'),
                 ('test.py', 'print "test"'),
                 ('hello/cruel/world.txt', 'Cruel?'))
        self.paths = set()
        for path, contents in files:
            realpath = makefile(self.tempdir, path, contents)
            self.paths.add(realpath)

    def tearDown(self):
        rmtree(self.tempdir)

    def test_dirlist_absfilenames(self):
        result = dirlist_absfilenames(self.tempdir)
        self.assertEquals(result, self.paths)


class TestLocalpathToS3path(TestCase):
    def setUp(self):
        self.tempdir = mkdtemp()
        makefile(self.tempdir, 'hello/world.txt', '')

    def tearDown(self):
        rmtree(self.tempdir)

    def test_localpath_to_s3path(self):
        s3path = localpath_to_s3path(self.tempdir, join(self.tempdir, 'hello/world.txt'), 'my/test')
        self.assertEquals(s3path, 'my/test/hello/world.txt')

    def test_s3path_to_localpath(self):
        localpath = s3path_to_localpath('mydir/', 'mydir/hello/world.txt', join(self.tempdir, 'my', 'test'))
        self.assertEquals(localpath, join(self.tempdir, 'my', 'test', 'hello', 'world.txt'))
