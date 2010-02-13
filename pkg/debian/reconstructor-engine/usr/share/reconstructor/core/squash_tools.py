#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
#    squash_tools.py   
#        Handles Squash Filesystem Operations
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
import commands
import logging
import tempfile
import fs_tools
import shutil
import time

log = logging.getLogger('squash_tools')

def create_squash_fs(mksquashfs_cmd=None, source_dir=None, dest_filename=None, overwrite=False):
    try:
        if source_dir and dest_filename:
            if not os.path.exists(source_dir): # make sure source exists
                log.error('Source directory %s does not exists...' % (source_dir))
                return False
            if overwrite:
                if os.path.exists(dest_filename):
                    # remove old file and create new
                    log.warn('Removing existing squash filesystem: %s' % (dest_filename))
                    os.remove(dest_filename)
                else:
                    log.warn('Unable to remove old squash filesystem: %s does not exist...' % (dest_filename))                    
            # create
            cmd = '%s %s %s' % (mksquashfs_cmd, source_dir, dest_filename)
            log.debug('Using command: %s' % (cmd))
            os.system(cmd)
            return True
        else:
            log.error('Source and destination must not be empty...')
            return False
    except Exception, d:
        log.error('Error creating squash filesystem: %s' % (d))
        return False
                
def extract_squash_fs(unsquashfs_cmd=None, filename=None, dest_dir=None):
    try:
        tmpMntSquashDir = os.path.join(tempfile.gettempdir(), 'r_sqfs')
        # check for existing dir
        if os.path.exists(dest_dir):
            log.warn('Removing existing extracted squash filesystem: %s' % (dest_dir))
            os.system('rm -Rf %s' % (dest_dir))
            while os.path.exists(dest_dir): # HACK: make sure directory is removed to continue...
                time.sleep(1)
            time.sleep(5)
            #if os.system('rm -Rf %s' % (dest_dir)) != 0:
            #    self.log.error('Error removing existing squash filesystem; check log...')
            #    return False
        # copy files
        log.info('Extracting Squash filesystem...')
        #shutil.copytree(tmpMntSquashDir, dest_dir, True) # copy true symlinks
        cmd = '%s -d %s %s' % (unsquashfs_cmd, dest_dir + '/', filename) # add trailing slash for rsync to copy contents
        log.debug('Using command: %s' % (cmd))
        os.system(cmd)
        return True
    except Exception, d:
        log.error('Error extracting squash filesystem: %s' % (d))
        return False
        
        
        
            
            
