#!/usr/bin/env python

"""Plays a pseudo-random sequence of songs.

Author: Caoilte Guiry
Name: random_music.py
License: BSD License

"""

from __future__ import with_statement
import os
import sys
import glob
from stat import ST_MTIME
from socket import gethostname
from random import randint
import subprocess
import datetime
import time
from ConfigParser import (ConfigParser, NoOptionError, NoSectionError,
                         MissingSectionHeaderError, RawConfigParser)
from optparse import OptionParser

__author__ = "Caoilte Guiry"
__copyright__ = "Copyright (c) 2011 Caoilte Guiry."
__version__ = "2.0.11"
__license__ = "BSD License"


class _Error(Exception):
    pass

class DirectoryNotFoundError(_Error):
    """The specified directory could not be found."""
    def __init__(self, dirname):
        self.dirname = dirname
        self.value = "The '%s' directory could not be found" % dirname
        Exception.__init__()
    def __str__(self):
        return repr(self.value)

class MissingConfigFileError(_Error):
    """Config file could not be found."""
    def __init__(self, config_file):
        self.config_file = config_file
        self.value = "The config file '%s' could not be found" % config_file
    def __str__(self):
        return repr(self.value)


def main():
    """Generate a playlist and start playing the songs."""
    if sys.platform in ["linux2", "darwin"]:
        try:
            rmp = RandomMusicPlaylist()
            rmp.play_music()
        except MissingConfigFileError:
            create_config_file(RandomMusicPlaylist._get_config_file(), 
                               RandomMusicPlaylist._get_home_dir())
            rmp = RandomMusicPlaylist()
            rmp.play_music()
    else:
        sys.stderr.write("Sorry, only Linux and Mac are currently supported")
        sys.exit(1)


def create_config_file(config_file, random_music_home):
    """Create a configuration file."""
    print "You do not appear to have a config file, lets create one!"
    config = RawConfigParser()
    config.add_section('config')
    config.set('config', 'loop_songs', 'true')
    config.set('config', 'randomise', 'true')
    config.set('config', 'index_dir', os.path.join(random_music_home, 
                                                   "indicies"))
    config.set('config', 'music_client', 'mplayer') # TODO: check exists?

    user_music_dirs = ""
    while not all([os.path.isdir(d) for d in user_music_dirs.split(",")]):
        user_music_dirs = raw_input("Input a csv list of full paths to "
                                   "your music dirs:")
    config.set('config', 'music_dirs', user_music_dirs)
            
    with open(config_file, 'wb') as fh:
        config.write(fh)

  
def check_is_dir(path):
    """Check if a directory exists."""
    if not os.path.isdir(path):
        raise DirectoryNotFoundError(path)

PATHNAME, SCRIPTNAME = os.path.split(sys.argv[0])
PATHNAME = os.path.abspath(PATHNAME)        

class RandomMusicPlaylist:
    """Generate and play random music playlists."""
    def __init__(self):
        self.load_config()
        self.process_flags()
        self.index_file = self.get_index_file()
        self.generate_list()

    @staticmethod
    def _get_home_dir():
        return os.path.join(os.path.expanduser("~"), ".random_music")

    @staticmethod    
    def _get_config_file():
        return os.path.join(os.path.expanduser("~"), ".random_music", "config.txt")


    def load_config(self):
        """Load configuration variables."""
        self.random_music_home = self._get_home_dir()
        if not os.path.isdir(self.random_music_home):
            os.makedirs(self.random_music_home)
            
        self.config_file = self._get_config_file()
        if not os.path.exists(self.config_file):
            raise MissingConfigFileError(self.config_file)
            
        config = ConfigParser()
        config.read(self.config_file)
        try:
            self.loop_songs = config.getboolean("config", "loop_songs")
            self.randomise = config.getboolean("config", "randomise")
            self.index_dir = config.get("config", "index_dir")
            self.music_client = config.get("config", "music_client")
            # music_dirs may be separated by commas. Unfortunately the
            # create_config_file() does not take account of this at the
            # moment. TODO: implement this
            self.music_dirs = config.get("config", "music_dirs").split(",") 
        except NoOptionError:
            print "No such option in config file"
            sys.exit(1)
        except NoSectionError:
            print "No such section in config file"
            sys.exit(1)
        except MissingSectionHeaderError:
            print "Failed to parse config file"
            sys.exit(1)
        
        # Verify that our music dirs are actually dirs
        for i, path in enumerate(self.music_dirs):
            try:
                check_is_dir(path)
            except DirectoryNotFoundError:
                # If an invalid directory was listed we want to remove it from 
                # the list and carry on. It is likely that the user provided a 
                # path containing a folder with a comma in the filename, so 
                # lets warn of that
                self.music_dirs.pop(i)
                print ("WARNING: The '%s' directory is invalid. Please review "
                        "your config file. Please note that directories must "
                        "not contain commas as these are used as a " 
                        "delimiter" % path)
                
                
        
        if not os.path.isdir(self.index_dir):
            print "Creating indicies path "+self.index_dir
            os.mkdir(self.index_dir)
            self.update_index()



    def process_flags(self):
        """Process command-line arguments and options."""
        default_music_client = self.music_client
        parser = OptionParser()
        parser.add_option("-u", "--update-index", action="store_true", 
                    dest="update_index", default=False, 
                    help="Update index file")
        parser.add_option("-r", "--randomise", action="store_true", 
                    dest="randomise", default=False, 
                    help="Randomise playlist") 
        #parser.add_option("-l", "--loop", action="store_true", 
        #           dest="loop_songs", default=self.loop_songs,
        #           help="Loop playlist")
        parser.add_option("-l", "--list-only", action="store_true",
                    dest="list_only", default=False, help="List songs only") 
                                        
        parser.add_option("-m", "--music-client", dest="music_client",
                    help="Set music_client. Default is "+default_music_client,
                    metavar="<music-client>", default=default_music_client)
        (options, args) = parser.parse_args()
        self.parse_search_terms(args)
                
        # If randomisation is explicitly set, we enable it outright.. if not
        # it depends on whether we've provided search terms or not
        if options.randomise:
            self.randomise = True
        elif self.search_terms:
            self.randomise = False
        
        if options.update_index:
            self.update_index()
            
        if options.list_only:
            self.music_client = "echo"  # FIXME: unix-only!
            self.loop_songs = False
        else:
            self.music_client = options.music_client
      
    def parse_search_terms(self, search_terms):
        """Convert search terms to a list (or a list of lists for OR 
        searches)."""
        # v. kludgish.. TODO: do this a little more gracefully
        self.search_terms, b = [], []
        for index, st in enumerate(search_terms):
            if st == "OR":
                self.search_terms.append(b)
                b = []
            else:
                b.append(st)

            if index+1 == len(search_terms):
                self.search_terms.append(b)
   
    def update_index(self):
        """Update the index file."""
        print ("Updating index. Depending on the size of your music "
              "collection this may take some time, so please be patient.")
        new_index_file = "%s/music_index_%s.txt" % (self.index_dir,
                        datetime.datetime.today().strftime("%Y%m%d_%H%M%S"))
        update_cmd = 'find %s -print -type f > "%s"'% \
               (" ".join("'%s'"%(d) for d in self.music_dirs), new_index_file)
        subprocess.check_call(update_cmd, shell=True)
        print "Music index updated (created index file '%s')" % \
              (new_index_file)
    
    def get_index_file(self):
        """Get the most up-to-date index file."""
        entries = sorted((os.stat(index_file)[ST_MTIME], index_file) 
                        for index_file in glob.glob(self.index_dir+"/*.txt"))
        if len(entries) == 0:
            raise Exception("Missing index file. "
                            "Try running program with -u flag")
        return entries[-1][-1]
    
    def generate_list(self):
        """Open the index file and generate a list of songs."""
        f = open(self.index_file)
        original_songs = [line.rstrip() for line in f.readlines()]
        
        if self.search_terms:
            # refine using search terms
            self.songs = []
            for st in self.search_terms:
                refined_songs = original_songs
                for s in st:
                    refined_songs = [song for song in refined_songs 
                                        if s.lower() in song.lower()]
                self.songs += sorted(refined_songs)
        else:
            self.songs = original_songs
        self.num_files = len(self.songs)



    def _get_song(self):
        index = self._get_song_index()
        return self.songs[index] 
        
        
    def _get_song_index(self):
        if self.randomise:
            song_index = randint(1, self.num_files)-1
        else:
            if (song_index+1) == self.num_files:
                if self.loop_songs:
                    song_index = 0
                else:
                    sys.exit(0)                    
            else:
                song_index += 1
                        
        return song_index
    
    def play_music(self):
        """Begin an infinite loop of songs."""
        song_index = -1 # FIXME: hack
        if self.num_files == 0:
            print "No songs found"
            sys.exit(0)
        
        # FIXME: spacebar/pause is an mplayer-specific command
        print "Press spacebar to pause songs"  
        print "Press ctrl+c once to skip a song"
        print "Hold ctrl+c to exit"
        print "%d files found." % self.num_files
        while True:
            try:
                song_index = self._get_song_index()
                song = self.songs[song_index]
                print "Playing song %d of %d" % (song_index+1, self.num_files)
                print self.clean_song_name(song)
                
                # Disabled the following as it got pretty annoying seeing a 
                # torrent of notifications for non-music files (mplayer 
                # gracefully skips these).            
                #try:
                #    notify_cmd="notify-send  -t 1000 '%s'" % \
                #                song.split("/")[-1]
                #    subprocess.check_call(notify_cmd, shell=True)
                #except:
                #    pass
                #FIXME: escape quotes in songs
                play_cmd = '"%s" "%s" > /dev/null 2>&1 ' % \
                           (self.music_client, song) 
                subprocess.check_call(play_cmd, shell=True)
            except KeyboardInterrupt:
                try:
                    # HACK to allow repeated ctrl+c to exit outright
                    time.sleep(0.1) 
                except KeyboardInterrupt:
                    print "\nExiting..."
                    sys.exit(0)

    def clean_song_name(self, songname):
        """Remove the music_dir from the beginning of the song name."""        
        # Reverse-sort the music_dirs list by string length, as if one 
        # music_dir is a subset of the other (e.g. "/music" and "/music/jazz"),
        #  we could end up cutting off too little
        for md in sorted(self.music_dirs, key=len, reverse=True):
            if songname.find(md) == 0:
                songname = songname.replace(md, "")
                break # shouldn't need to do any more replacements
        return songname
        
if __name__ == "__main__":
    sys.exit(main())
