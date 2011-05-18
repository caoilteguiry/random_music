#!/usr/bin/env python

from __future__ import with_statement
import os
import sys
import glob
from stat import S_ISREG, ST_MTIME, ST_MODE
from socket import gethostname
from random import randint
import subprocess
import signal
import datetime
import time
from ConfigParser import *
from optparse import OptionParser

"""
Author: Caoilte Guiry
Name: random_music.py
Description: Plays a pseudo-random sequence of songs.
License: BSD License
"""

class DirectoryNotFoundException(Exception):
    def __init__(self, dirname):
        self.dirname=dirname
        self.value="The '%s' directory could not be found" % dirname
    def __str__(self):
        return repr(self.value)

def main():
    if sys.platform in ["linux2", "darwin"]:
        rmp = RandomMusicPlaylist()
        rmp.playMusic()
    else:
        print "Sorry, only Linux and Mac are currently supported"
        sys.exit(0)
  
def checkDir(dir):
    if not os.path.isdir(dir):
        raise DirectoryNotFoundException(dir)

pathname, scriptname = os.path.split(sys.argv[0])
pathname = os.path.abspath(pathname)        

class RandomMusicPlaylist:
    def __init__(self):
        self.loadConfig()
        self.processFlags()
        self.index_file = self.getIndexFile()
        self.generateList()

    def loadConfig(self):
        """ Load configuration variables """
        self.config_file = pathname+"/config.txt"
        if not os.path.exists(self.config_file):
            self.createConfigFile()
            
        config = ConfigParser()
        config.read(self.config_file)
        try:
            self.loop_songs = config.getboolean("config", "loop_songs")
            self.randomise = config.getboolean("config", "randomise")            
            self.index_dir = config.get("config", "index_dir")
            self.music_client = config.get("config", "music_client")
            self.music_dirs = [config.get("config", "music_dirs")] # TODO: convert csv to list
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
        for dir in self.music_dirs:
            checkDir(dir)
        
        if not os.path.isdir(self.index_dir):
            print "Creating indicies dir "+self.index_dir
            os.mkdir(self.index_dir)
            self.updateIndex()

    def createConfigFile(self):
        """ Create a configuration file. """
        print "You do not appear to have a config file, lets create one!"
        config = RawConfigParser()
        config.add_section('config')
        config.set('config', 'loop_songs', 'true')
        config.set('config', 'randomise', 'true')
        config.set('config', 'index_dir', pathname+'/indicies')
        config.set('config', 'music_client', 'mplayer')

        user_music_dir = ""
        while not os.path.isdir(user_music_dir):
            user_music_dir = raw_input("Input full path to your music dir:")
        config.set('config', 'music_dirs', user_music_dir)
                
        with open(self.config_file, 'wb') as configfile:
            config.write(configfile)        

    def processFlags(self):
        """ Process command-line arguments and options """
        default_music_client = self.music_client
        parser = OptionParser()
        parser.add_option("-u", "--update-index", action="store_true", 
                    dest="update_index", default=False, 
                    help="Update index file")
        parser.add_option("-r", "--randomise", action="store_true", 
                    dest="randomise", default=False, help="Randomise playlist") 
        #parser.add_option("-l", "--loop", action="store_true", 
        #            dest="loop_songs", default=self.loop_songs,help="Loop playlist")
        parser.add_option("-l", "--list-only", action="store_true",
                          dest="list_only", default=False, 
                          help="List songs only")                    
        parser.add_option("-m", "--music-client", dest="music_client",
                    help="Set music_client. Default is "+default_music_client,
                    metavar="<music-client>", default=default_music_client)
        (options, args) = parser.parse_args()
        self.parseSearchTerms(args)
                
        # If randomisation is explicitly set, we enable it outright.. if not
        # it depends on whether we've provided search terms or not
        if options.randomise:
            self.randomise=True
        elif self.search_terms:
            self.randomise=False
        
        if options.update_index:
            self.updateIndex()
            
        if options.list_only:
            self.music_client="echo"  # FIXME: unix-only!
            self.loop_songs=False
        else:
            self.music_client=options.music_client
      
    def parseSearchTerms(self, search_terms):
        """ Convert search terms to a list (or a list of lists for OR searches) """
        # v. kludgish.. TODO: do this a little more gracefully
        a = []
        b = [] 
        for index, st in enumerate(search_terms):
            if st=="OR":
                a.append(b)
                b=[]
            else:
                b.append(st)
            if index+1==len(search_terms):
                a.append(b)
        self.search_terms = a
   
    def updateIndex(self):
        """ Update the index file """
        print ("Updating index. Depending on the size of your music collection "
              "this may take some time, so please be patient.");        
        new_index_file="%s/music_index_%s.txt" % (self.index_dir,
                        datetime.datetime.today().strftime("%Y%m%d_%H%M%S"))
        update_cmd='find %s -print -type f > "%s"'%\
                   (" ".join("'%s'"%(d) for d in self.music_dirs), new_index_file)
        subprocess.check_call(update_cmd, shell=True)
        print "Music index updated (created index file '%s')" %\
              (new_index_file)
    
    def getIndexFile(self):
        """ Get the most up-to-date index file """
        entries = sorted((os.stat(index_file)[ST_MTIME], index_file) 
                        for index_file in glob.glob(self.index_dir+"/*.txt"))
        if len(entries)==0:
            raise Exception("Missing index file. Try running program with -u flag")
        return entries[-1][-1]
    
    def generateList(self):
        """ Open the index file and generate a list of songs """
        f=open(self.index_file)
        original_songs=[line.rstrip() for line in f.readlines()]
        
        if self.search_terms:
            # refine using search terms
            self.songs=[]
            for st in self.search_terms:
                refined_songs = original_songs
                for s in st:
                    refined_songs=[song for song in refined_songs if s.lower() in song.lower()]
                self.songs+=sorted(refined_songs)
        else:
            self.songs=original_songs

    
    def playMusic(self):
        """ Begin an infinite loop of songs """
        song_index=-1; # FIXME: hack
        self.num_files = len(self.songs)
        if self.num_files==0:
            print "No songs found"
            sys.exit(0)
        
        print "Press spacebar to pause songs"  # FIXME: mplayer-specific command
        print "Press ctrl+c once to skip a song"
        print "Hold ctrl+c to exit"
        print "%d files found." % self.num_files
        while True:
            try:
                if self.randomise:
                    song_index = randint(1,self.num_files)-1
                else:
                    if (song_index+1)==self.num_files:
                        if self.loop_songs:
                            song_index=0;
                        else:
                            sys.exit(0)                    
                    else:
                        song_index+=1;
                                
                song = self.songs[song_index]
                print "Playing song %d of %d" %(song_index+1, self.num_files)
                print song
                
                # Disabled the following as it got pretty annoying seeing a torrent
                # of notifications for non-music files (mplayer gracefully skips these).            
                #try:
                #    notify_cmd="notify-send  -t 1000 '%s'" % song.split("/")[-1]
                #    subprocess.check_call(notify_cmd, shell=True)
                #except:
                #    pass
                #FIXME: escape quotes in songs
                play_cmd='"%s" "%s" > /dev/null 2>&1 ' %\
                           (self.music_client, song) 
                subprocess.check_call(play_cmd, shell=True)
            except KeyboardInterrupt:
                try:
                    time.sleep(0.1) # HACK to allow repeated ctrl+c to exit outright
                except KeyboardInterrupt:
                    print "\nExiting..."
                    sys.exit(0) 
if __name__=="__main__":
    sys.exit(main())
