#!/usr/bin/env python
#
#  iso_tools.py
#        Handles ISO operations
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

from reconstructor import settings
import logging
import os
import tempfile
import time
from reconstructor.core import fs_tools

log = logging.getLogger('IsoTools')

def extract(iso_filename=None, target_dir=None):
    '''Extracts ISO contents into target_dir'''
    try:
        # mount iso as loopback device
        # temporary mount point
        tmpMntDir = os.path.join(tempfile.gettempdir(), 'r_mnt')
        if not fs_tools.mount(iso_filename, tmpMntDir):
            log.error('ISO was not mounted correctly; Check log file for details.')
            return
        # check to make sure iso was mounted
        if len(os.listdir(tmpMntDir)) == 0:
            log.error('ISO was not mounted correctly; Check log file for details.')
            return
        # copy files
        # check for existing directory
        if os.path.exists(target_dir):
            log.warn('Removing existing extracted ISO directory...')
            os.system('rm -Rf %s' % (target_dir))
            while os.path.exists(target_dir): # HACK: make sure directory is deleted...
                time.sleep(1)
            time.sleep(5)
        else:
            # create target_dir
            log.info('Destination directory does not exist; creating...')
            os.makedirs(target_dir)
        # copy
        log.info('Copying files... Please wait...')
        os.system('rsync -a %s %s' % (tmpMntDir + os.sep, target_dir + os.sep))
        #shutil.copytree(tmpMntDir, self.__iso_fs_dir, True) # copy true symlinks
        #self.log.debug(commands.getoutput('rsync -avz %s %s' % (tmpMntDir, self.__iso_fs_dir))) # test fails with rsync??.... :|
        return True
    except Exception, d:
        log.error('Error extracting ISO: %s' % (d))
        return False
    finally:
        # clean up
        if not fs_tools.unmount(tmpMntDir):
            log.error('Error unmounting %s; check log for details...' % (tmpMntDir))
            
def create(description=None, src_dir=None, dest_file=None):
    if src_dir and dest_file:
        log.info('Creating ISO...')
        # reduce description to 32 chars -- max supported by ISO
        desc = description[:32]
        update_md5sums(src_dir=src_dir)
        os.system('mkisofs -o %s -b \"isolinux/isolinux.bin\" -c \"isolinux/boot.cat\" -no-emul-boot -boot-load-size 4 -boot-info-table -V \"%s\" -cache-inodes -r -J -l \"%s\"' % (dest_file, desc, src_dir))
        return True
    else:
        log.debug('%s %s %s' % (desc, src_dir, dest_file))
        log.error('You must specify source directory and destination file...')
        return False

def burn():
    raise RuntimeError, "Not yet implemented..."
    
def update_md5sums(src_dir=None):
    if os.path.exists(src_dir):
        log.info('Updating md5sums...')
        os.system('cd %s ; find . -type f -print0 | xargs -0 md5sum > md5sum.txt' % (src_dir))
        return True
    else:
        log.error('Path does not exist: %s' % (src_dir))
        return False

def add_id(src_dir=None):
    if os.path.exists(src_dir):
        log.debug('Adding Disc ID...')
        f = open(os.path.join(src_dir, '.disc_id'), 'w')
        f.write('Built with Reconstructor %s\n\t%s\n%s' % (str(settings.APP_VERSION), settings.APP_COPYRIGHT, settings.APP_URL))
        f.close()
        return True
    else:
        log.error('Path does not exist: %s' % (src_dir))
        return False
        
        
        
