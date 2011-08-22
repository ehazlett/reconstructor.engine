#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
#    fs_tools.py   
#        Miscellaneous tools for working with the filesystem
#
#    Copyright (C) 2010  Lumentica
#       http://www.lumentica.com
#       info@lumentica.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import shutil
import logging
import commands

log = logging.getLogger('fs_tools')

def mount(src_file=None, dest_dir=None):
    '''Mounts src_file to dest_dir'''
    try:
        if not os.path.exists(src_file): # make sure source exists
            log.error('Source file %s does not exist...' % (src_file))
            return False
        if not os.path.exists(dest_dir):
            log.debug('Creating mount point: %s' % (dest_dir))
            os.makedirs(dest_dir)
        log.debug('Using mount command: mount -v -o loop %s %s' % (src_file, dest_dir))
        # HACK: capture the output from the command and format chars to fit output from mount on one line
        cmd = commands.getoutput('mount -v -o loop %s %s' % (src_file, dest_dir)).split('\n')
        if commands.getoutput('mount | grep %s' % (dest_dir)):
            return True
        else:
            return False
    except Exception, d:
        import traceback
        traceback.print_exc()
        log.error('Error mounting %s: %s' % (src_file, d))
        return False
        
def unmount(mount_dir=None):
    '''Unmounts specified mount_dir'''
    try:
        info = os.stat(mount_dir)
        # check to see if mount_dir is a device and skip path check if so...
        if info.st_rdev == 0:
            if not os.path.exists(mount_dir): # make sure file exists
                log.error('Mount directory %s does not exist' % (mount_dir))
                return False
        # unmount
        log.debug('Unmounting %s...' % (mount_dir))
        os.system('umount -f %s' % (mount_dir))
        # check to see if a device
        if info.st_rdev == 0:
            # remove dir if necessary
            if os.path.exists(mount_dir):
                log.debug('Removing temporary mount dir: %s' % (mount_dir))
                shutil.rmtree(mount_dir)
        return True
    except Exception, d:
        log.error('Error unmounting %s: %s' % (mount_dir, d))
        return False
        
def bind_mount(source=None, target_dir=None):
    try:
        commands.getoutput('mount --bind %s %s' % (source, target_dir))
        return True
    except Exception, d:
        log.error('Error mounting /proc: %s' % (d))
        return False

def unmount_bind(target_dir):
    try:
        os.system('umount %s' % (target_dir))
        return True
    except Exception, d:
        log.error('Error unmounting %s: %s' % (target_dir, d))
        return False
