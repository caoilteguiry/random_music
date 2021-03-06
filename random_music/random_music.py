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

from utils import which
from _exceptions import DirectoryNotFoundError, MissingConfigFileError

__author__ = "Caoilte Guiry"
__copyright__ = "Copyright (c) 2013 Caoilte Guiry."
__version__ = "2.1.17"
__license__ = "BSD License"



# Get some info about execution env...
PATHNAME, SCRIPTNAME = os.path.split(sys.argv[0])
PATHNAME = os.path.abspath(PATHNAME)        

# Set some defaults...
DEFAULT_HOME_DIR = os.path.join(os.path.expanduser("~"), ".random_music") 
DEFAULT_CONFIG_FILE = os.path.join(DEFAULT_HOME_DIR, "config.txt")
DEFAULT_MUSIC_CLIENT = "mplayer"

def main():
    """
    Parse user args, generate a playlist and start playing the songs.
    """
    parser = OptionParser()
    parser.add_option("-u", "--update-index", action="store_true", 
                dest="update_index", default=False, 
                help="Update index file")
    parser.add_option("-r", "--randomise", action="store_true", 
                dest="force_randomise", default=False, 
                help="Force randomisation when using search terms.") 
    # TODO: implement this
    #parser.add_option("-l", "--loop", action="store_true", 
    #           dest="loop_songs", default=self.loop_songs,
    #           help="Loop playlist")
    parser.add_option("-l", "--list-only", action="store_true",
                dest="list_only", default=False, help="List songs only") 
    parser.add_option("-c", "--config_file",
                dest="config_file", help="Configuration file", default=DEFAULT_CONFIG_FILE)
    parser.add_option("-n", "--num-songs",
            dest="num_songs", help="Number of songs to generate/play")


    (options, args) = parser.parse_args()
    
    # Try to create a playlist. 
    have_playlist = False
    while not have_playlist:    
        try:        
            rmp = RandomMusicPlaylist(config_file=options.config_file, search_terms=args, update_index=options.update_index, 
                                      force_randomise=options.force_randomise, 
                                      list_only=options.list_only, num_songs=options.num_songs)
            have_playlist = True
        except MissingConfigFileError, err_msg:
            sys.stderr.write("%s\n" % err_msg)
            create_config_file(options.config_file, 
                               DEFAULT_HOME_DIR)
    
    rmp.play_music()


def create_config_file(config_file, random_music_home):
    """
    Create a configuration file.

    :param config_file: path to config file we are creating
    :type config_file: str
    :param random_music_home: home of random_music application (i.e. where 
    index files are stored
    :type random_music_home: str
    """
    sys.stdout.write("You do not appear to have a config file, lets create one!\n")
    sys.stdout.write("Creating config file at %s\n" % config_file)
    config = RawConfigParser()
    config.add_section('config')
    config.set('config', 'loop_songs', 'true')
    config.set('config', 'randomise', 'true')
    config.set('config', 'index_dir', os.path.join(random_music_home, 
                                                   "indicies"))
    music_client = DEFAULT_MUSIC_CLIENT
    while not which(music_client):
        music_client = raw_input("The music player '%s' could not be found "
                                   "on your path. Please input a different "
                                   "music player:" % music_client)   
    
    config.set('config', 'music_client', music_client) 

    user_music_dirs = ""
    while not all([os.path.isdir(d) for d in user_music_dirs.split(",")]):
        user_music_dirs = raw_input("Input a csv list of full paths to "
                                   "your music dirs:")
    config.set('config', 'music_dirs', user_music_dirs)
            
    with open(config_file, 'wb') as fh:
        config.write(fh)

  
def check_is_dir(path):
    """
    Check if a directory exists. Raise a DirectoryNotFoundError exception if
    not.

    :param path: path we are checking
    :type path: str
    """
    if not os.path.isdir(path):
        raise DirectoryNotFoundError(path)


class RandomMusicPlaylist(object):
    """
    Generate and play random music playlists.
    """
    def __init__(self, config_file, search_terms=None, update_index=False, 
                                  force_randomise=False, list_only=False, num_songs=None):
        """
        :param config_file: path to configuration file (optional)
        :type config_file: str
        :param search_terms: a list of search terms against which the playlist
        should be generated. Optional, defaults to an empty list (i.e. find
        all songs)
        :type search_terms: list
        :param update_index: boolean value which denotes whether or not we want
        to update the songs index or not.
        :type update_index: bool
        :param force_randomise: boolean value which denotes whether or not we 
        want to force randomisation. The default behaviour is to randomise 
        when no search terms are supplied, and not to randomise if search terms
        are supplied (typically a user will want to listen to an album in 
        sequence); this option, when set to true, will randomise in spite of 
        the method of invocation.
        :type force_randomise: bool
        :param list_only: if set to true, we do not play any songs, just list them.
        :type list_only: bool
        :param num_songs: Number of songs to generate (defaults to all found)
        :type num_songs: int
        """
        self.random_music_home = DEFAULT_HOME_DIR
        if not os.path.isdir(self.random_music_home):
            os.makedirs(self.random_music_home)
            
        self.config_file = config_file
            
        if search_terms:
            self.search_terms = search_terms
        else:
            self.search_terms = []
            
        self.update_index = update_index
        self.force_randomise = force_randomise
        self.list_only = list_only
            
        try:                                                                         
            self.num_songs = int(num_songs)                                          
        except (TypeError, ValueError):                                              
            # Covers the case where a non-numeric val was passed, or None was passed.
            self.num_songs = None                                                    
                                                                             


        self.load_config()
        self.process_flags()
        self.index_file = self.get_index_file()
        self.generate_list()


    def load_config(self):
        """
        Load configuration variables from config file.
        """
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
            sys.stderr.write("No such option in config file\n")
            sys.exit(1)
        except NoSectionError:
            sys.stderr.write("No such section in config file\n")
            sys.exit(1)
        except MissingSectionHeaderError:
            sys.stderr.write("Failed to parse config file\n")
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
                sys.stdout.write("WARNING: The '%s' directory is invalid. Please review "
                                 "your config file. Please note that directories must "
                                 "not contain commas as these are used as a " 
                                 "delimiter\n" % path)
        
        if not os.path.isdir(self.index_dir):
            sys.stdout.write("Creating indicies path %s\n" % self.index_dir)
            os.mkdir(self.index_dir)
            self._update_index()


    def process_flags(self):
        """
        Process command-line arguments and options.
        """
        self.parse_search_terms(self.search_terms)
                
        # If randomisation is explicitly set, we enable it outright.. if not
        # it depends on whether we've provided search terms or not
        if self.force_randomise:
            self.randomise = True
        elif self.search_terms:
            self.randomise = False
        
        if self.update_index:
            self._update_index()
            
        if self.list_only:
            self.music_client = "echo"  # FIXME: unix-only!
            self.loop_songs = False
      
    def parse_search_terms(self, search_terms):
        """
        Convert search terms to a list (or a list of lists for OR 
        searches).

        :param search_terms: terms against which files will be matched
        :type search_terms: list[str]
        """
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
   
    def _update_index(self):
        """
        Update the index file.
        """
        start_time = datetime.datetime.now()
        sys.stdout.write("Updating index. Depending on the size of your music "
                         "collection this may take some time, so please be patient. "
                         "(Update started at %s)\n" % start_time)
        new_index_file = "%s/music_index_%s.txt" % (self.index_dir,
                        start_time.strftime("%Y%m%d_%H%M%S"))
        files = (os.path.join(tup[0], f) for d in self.music_dirs 
                                         for tup in os.walk(d) 
                                         for f in tup[2] )
        
        with open(new_index_file, "w") as fh:
            for filename in files:
                fh.write("%s\n" % filename)
            
        end_time = datetime.datetime.now()
        sys.stdout.write("Music index updated (created index file '%s')\n" 
                         "Update duration:%s\n" % 
                         (new_index_file, end_time - start_time))
    
    def get_index_file(self):
        """
        Get the most up-to-date index file.
        """
        entries = sorted((os.stat(index_file)[ST_MTIME], index_file) 
                        for index_file in glob.glob(self.index_dir+"/*.txt"))
        if len(entries) == 0:
            raise Exception("Missing index file. "
                            "Try running program with -u flag")
        return entries[-1][-1]
    
    def generate_list(self):
        """
        Open the index file and generate a list of songs.
        """
        with open(self.index_file, "r") as fh:
            original_songs = [line.rstrip() for line in fh.readlines()]
        
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
        
        # If we've specified a num_songs, slice out this much
        if self.num_songs:                                 
            self.songs[:] = self.songs[:self.num_songs]    
        else:
            self.num_songs = len(self.songs)


    def _get_song_index(self, song_index):
        """
        Get the next song index. If we are in random mode, we generate a
        random index, otherwise we increment the index. However, we want
        to reset the index to 0 if we've reached the end, or exit if 
        we've specified that we don't want to loop songs.

        :param song_index: current song index
        :type song_index: int
        """ 
        if self.randomise:
            song_index = randint(1, self.num_songs) - 1
        else:
            if (song_index + 1) == self.num_songs:
                if self.loop_songs:
                    song_index = 0
                else:
                    return None
            else:
                song_index += 1
        return song_index
    

    # TODO: this should be decoupled
    def play_music(self):
        """
        Begin an infinite loop of songs.
        """
        song_index = -1
        if self.num_songs  == 0:
            sys.stdout.write("No songs found\n")
            sys.exit(0)
        
        # FIXME: spacebar/pause is an mplayer-specific command
        sys.stdout.write("Press spacebar to pause songs\n")
        sys.stdout.write("Press ctrl+c once to skip a song\n")
        sys.stdout.write("Hold ctrl+c to exit\n")
        sys.stdout.write("%d files found.\n" % self.num_songs)
        while True:
            try:
                song_index = self._get_song_index(song_index)
                if song_index == None:
                    sys.exit(0)
                song = self.songs[song_index]
                sys.stdout.write("%s\n" % song)
                
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
                    sys.stderr.write("\nExiting...\n")
                    sys.exit(0)

    # TODO: decouple this
    def clean_song_name(self, songname):
        """
        Remove the music_dir from the beginning of the song name, e.g. given a
        songname of '/home/caoilte/music/Punk/foo.mp3' and music_dirs of
        ['/home/caoilte/music'] return '/Punk/foo.mp3'.

        :param songname: the abs path to the song we want to 'clean'
        :type songname: str
        """
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
