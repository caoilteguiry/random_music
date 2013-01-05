

import os
import unittest2

from random_music import random_music


class TestWhich(unittest2.TestCase):
    def setUp(self):
        """
        Mock os.environ['PATH'] & os.path.exists to have predictable
        outputs.
        """
        self.old_path = random_music.os.environ['PATH']
        random_music.os.environ['PATH'] = os.pathsep.join(['/usr/local/sbin', 
                                               '/usr/local/bin', '/usr/sbin', 
                                               '/usr/bin', '/sbin', '/bin'])
        self.old_exists = random_music.os.path.exists
        random_music.os.path.exists = lambda path: path == '/usr/local/bin/lsmod'

    def tearDown(self):
        """
        Restore os.environ['PATH'] & os.path.exists
        """
        random_music.os.environ['PATH'] = self.old_path
        random_music.os.path.exists = self.old_exists


    def test_paths(self):
        """
        Test some paths. Mocking in setUp should dictate that we find
        lsmod, but nothing else (e.g. dmesg).
        """
        res = random_music.which('lsmod')
        expected = '/usr/local/bin/lsmod'
        self.assertEqual(res, expected)

        res = random_music.which('dmesg')
        expected = None
        self.assertEqual(res, expected)


class TestCheckIsDir(unittest2.TestCase):
    def setUp(self):
        """
        Mock os.path.isdir to behave predictably.
        """
        self.old_isdir = random_music.os.path.isdir
        random_music.os.path.isdir = lambda x: x == '/tmp'

    def tearDown(self):
        """
        Restore os.path.isdir
        """
        random_music.os.path.isdir = self.old_isdir

    def test_paths(self):
        """
        Test some paths. Mocking in setUp should dictate that we find
        /tmp, but nothing else
        """
        # This should pass ok
        random_music.check_is_dir('/tmp')
        # This shouldn't
        self.assertRaises(random_music.DirectoryNotFoundError, random_music.check_is_dir, '/foo')
