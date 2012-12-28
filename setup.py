#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from random_music.random_music import __version__

setup(
    name = u"random_music",
    version = __version__,
    author = u"Caoilte Guiry",   
    author_email = u"", 
    license='BSD License',
    description = u"Plays a pseudo-random sequence of songs",
    long_description = open(u'README').read(),
    packages = find_packages(),
    entry_points = {
        'console_scripts': ['music = random_music.random_music:main']
    },
)
