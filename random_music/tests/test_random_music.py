

import os
import unittest2

from random_music import random_music, utils


class TestWhich(unittest2.TestCase):
    def setUp(self):
        """
        Mock os.environ['PATH'] & os.path.exists to have predictable
        outputs.
        """
        self.old_path = utils.os.environ['PATH']
        utils.os.environ['PATH'] = os.pathsep.join(['/usr/local/sbin', 
                                               '/usr/local/bin', '/usr/sbin', 
                                               '/usr/bin', '/sbin', '/bin'])
        self.old_exists = utils.os.path.exists
        utils.os.path.exists = lambda path: path == '/usr/local/bin/lsmod'

    def tearDown(self):
        """
        Restore os.environ['PATH'] & os.path.exists
        """
        utils.os.environ['PATH'] = self.old_path
        utils.os.path.exists = self.old_exists


    def test_paths(self):
        """
        Test some paths. Mocking in setUp should dictate that we find
        lsmod, but nothing else (e.g. dmesg).
        """
        res = utils.which('lsmod')
        expected = '/usr/local/bin/lsmod'
        self.assertEqual(res, expected)

        res = utils.which('dmesg')
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
        self.assertRaises(random_music.DirectoryNotFoundError, 
                          random_music.check_is_dir, '/foo')


class TestCreatConfigFile(unittest2.TestCase):
    def setUp(self):
        """
        Mock RawConfigParser, which, raw_input, os.path.isdir, open
        """
        # Prevent the config parser from attempting to write to disk
        self.old_rcp_write = random_music.RawConfigParser.write
        random_music.RawConfigParser.write = lambda *args: None

        # Want which() to return False first so we will cover within the while
        # block (the `while not which(music_client)` block, specifically), 
        # then answer True so we can carry on. Create a which_answers 
        # generator to satisfy this requirement
        which_answers = (ans for ans in (False, True))
        self.old_which = random_music.which
        random_music.which = lambda path: which_answers.next()

        # Want raw_input to output a CSV path the second time around.
        # The first time, it doesn't really matter what is returned 
        # since the flow is controlled by the which_answers generator above.
        music_dirs = '/home/caoilte/music,/media/music'
        ri_answers = (ans for ans in ('mplayer', music_dirs))
        self.old_raw_input = raw_input
        random_music.raw_input = lambda q: ri_answers.next()

        # Want os.path.isdir to respond True to the CSV music dirs above
        self.old_isdir = random_music.os.path.isdir
        random_music.os.path.isdir =  lambda path: path.rstrip('/') in music_dirs.split(",")


        # Finally want to mock open(), so we don't open any files
        class mopen(object):
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self, *args, **kwargs):
                return None
        
            def __exit__(self, *args, **kwargs):
                pass

        self.old_open = open
        random_music.open = mopen


    def tearDown(self):
        """
        Restore mocked objects/functions.
        """
        random_music.RawConfigParser.write = self.old_rcp_write 
        random_music.which = self.old_which 
        raw_input = self.old_raw_input 
        random_music.os.isdir = self.old_isdir 
        open = self.old_open 


    def test_create(self):
        random_music.create_config_file('/home/caoilte/config.txt', '/home/caoilte/.random_music/')

     

