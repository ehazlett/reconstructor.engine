#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
#   engine.py   
#       Main script for Reconstructor
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
import platform
import sys
# set path
sys.path.append(os.path.dirname(os.getcwd()))    
import logging
import commands
from optparse import OptionParser
import shutil
import tempfile
import stat
import time
import glob
import tarfile
import urllib
import urllib2
import re
import gzip
import httplib
from random import Random
import string
import datetime
from decimal import Decimal
import threading
from reconstructor import settings
from reconstructor.core import fs_tools
from reconstructor.core import iso_tools
from reconstructor.core import squash_tools
from reconstructor.core.distro import ubuntu, ubuntu_ec2, centos, debian
from reconstructor.config import Project

# logging vars
LOG_LEVEL=settings.LOG_LEVEL
LOG_FILE='build.log'
LOG_CONFIG=logging.basicConfig(level=logging.DEBUG, # always log debug to file
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d-%Y %H:%M:%S',
                    filename=LOG_FILE,
                    filemode='w')
                
logging.config=LOG_CONFIG
console = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s: %(message)s')
console.setFormatter(formatter)
console.setLevel(LOG_LEVEL)
logging.getLogger('').addHandler(console)
log = logging.getLogger('CoreApp')

# custom logging handler for gtk textview
class TextBufferHandler(logging.Handler):
    def __init__(self, textbuffer=None):
        logging.Handler.__init__(self)
        # setup textbuffer
        if not textbuffer:
            print('You must specify a textbuffer for the log handler.')
        self.textbuffer = textbuffer

    def emit(self, record):
        txt = ''
        #if self.textbuffer.get_char_count() > 0:
        #    txt = self.textbuffer.get_text()
        #self.textbuffer.set_text(txt + '\n' + record.message)
        #self.textbuffer.insert_at_cursor(self.format(record)+'\n', 0) # will format
        self.textbuffer.insert_at_cursor(record.message+'\n', 0) # only send message

# global functions
def check_depends():
    depends = ['mksquashfs', 'genisoimage', 'syslinux', 'rsync', 'fuser', 'kpartx', 'parted', 'mkfs.vfat', 'install-mbr', 'fakeroot', 'dpkg-buildpackage']
    deps = ''
    for d in depends:
        if commands.getoutput('which %s' % (d)) == '':
            # specify package name if different from depends list name
            if d == 'mksquashfs':
                deps += '%s ' % ('squashfs-tools')
            elif d == 'fuser':
                deps += '%s ' % ('psmisc')
            elif d == 'mkfs.vfat':
                deps += '%s ' % ('dosfstools')
            elif d == 'install-mbr':
                deps += '%s ' % ('mbr')
            elif d == 'dpkg-buildpackage':
                deps += '%s ' % ('dpkg-dev')
            else:
                deps += '%s ' % (d)
    return deps
    
def check_iso_repo():
    if settings.ONLINE_ISO_REPO != '':
        if not os.path.exists(settings.ONLINE_ISO_REPO):
            log.info('Creating ISO repository...')
            os.makedirs(settings.ONLINE_ISO_REPO)

def create_lvm_volume(lvm_base=None):
    if lvm_base:
        # check for lvm base volume
        s = commands.getoutput('lvs | grep %s' % (lvm_base))
        #print(s)
        if s == '':
            log.error('LVM volume base %s does not exist' % (lvm_base))
            sys.exit(1)
        log.info('Using LVM volume %s for source...' % (lvm_base))
        log.debug('Creating temporary mount point for working directory...')
        # create temporary name for mount point
        tmp_lvm_name = ''.join(Random().sample('abcdefghijk1234567890', 4))
        # check to make sure volume was created... try 5 times then return fail
        count = 0
        lvs = ''
        lvm_found = False
        while count < 5:
            lvs = commands.getoutput('lvs | grep %s' % (tmp_lvm_name))
            if lvs.find(tmp_lvm_name) > -1:
                lvm_found = True
                break
            else:
                os.system('lvcreate -L 8G -s %s -n %s' % (os.path.join(settings.LVM_ROOT, lvm_base), tmp_lvm_name))
            count += 1
            # sleep for 2 seconds
            time.sleep(2)

        if not lvm_found:
            log.error('Unable to create LVM volume...')
            return False
        # mount new snapshot to working dir
        tmp_dir = os.path.join(tempfile.gettempdir(), tmp_lvm_name)
        os.makedirs(tmp_dir)
        os.system('mount %s %s' % (os.path.join(settings.LVM_ROOT, tmp_lvm_name), tmp_dir))
        return tmp_dir
    else:
        log.error('You must specify an lvm base volume.')
        sys.exit(1)

def check_queue():
    try:
        # check for free disk space
        r = re.compile('^[\/,:,.]*\S*\s*\S*\s*\S*\s*([\d,.]*)(\w*)\s')
        df_total = commands.getoutput('df -h %s' % (settings.ONLINE_ISO_REPO)).split('\n')
        # HACK: if using NFS, the df -h command will split it to another line; so check and if NFS, get the 3rd line instead
        if not df_total[1].startswith('/') or df_total[1].startswith('//'):
            df = df_total[2]
        else:
            df = df_total[1]
        size = (r.match(df).group(1) + ' ' + r.match(df).group(2)).split(' ')
        free_space = True
        if size[1].lower() == 'm':
            if float(size[0])/1024 < float(settings.MINIMUM_BUILD_FREE_SPACE):
                free_space = False
        elif size[1].lower() == 'g':
            # check if more than 2G free
            if float(size[0]) < float(settings.MINIMUM_BUILD_FREE_SPACE):
                free_space = False
        if not free_space:
            log.error('Not enough free space on %s (%s) for build. At least %sG is needed for build.' % (settings.ONLINE_ISO_REPO, size[0]+size[1], settings.MINIMUM_BUILD_FREE_SPACE))
            # TODO: send notification for free space error
            # update web app with status 
#            try:
#                values = {'action': 'server', 'value': 'no_space' }
#                data = urllib.urlencode(values)
#                req = urllib2.Request(# NEED URL, data)
#                urllib2.urlopen(req) 
#            except Exception, d:
#                log.warning('Unable to update job status: %s', (d))
#                pass
    
        else:
            chars = string.letters + string.digits
            fname = ''.join(Random().sample(chars, 5)) + '.rpj'
            bundle_path = os.path.join(tempfile.gettempdir(), fname)
            r = urllib.urlretrieve(settings.QUEUE_URL, bundle_path)
            log.debug('Content-type: %s' % r[1]['content-type'])
            g = gzip.open(bundle_path)
            try:
                g._read_gzip_header() # will throw an exception if not gzip file
                log.debug('Received project file: %s' % (r[0]))
                # start reconstructor with project
                log.info('Launching Reconstructor...')
                os.system('python %s -f %s' % (__file__, r[0]))
                # cleanup project file
                os.remove(r[0])
                log.info('Finished job: %s' % (r[0]))
            except:
                log.debug('Not a valid project file: %s' % (r[0]))
                os.remove(r[0])
            finally:
                g.close()
    except Exception, d:
        log.error('Error checking queue: %s' % (d))

def start_queue_watcher():
    '''Starts the Reconstructor Queue watcher for online jobs'''
    log.info('Starting Reconstructor Queue Watcher...')
    log.debug('Watching for jobs at: %s' % (settings.QUEUE_URL))
    log.debug('Checking for jobs every %s seconds' % (settings.QUEUE_CHECK_INTERVAL))
    # start queue
    try:
        while True:
            check_queue()
            # wait to check for new job
            time.sleep(settings.QUEUE_CHECK_INTERVAL)
    except KeyboardInterrupt:
        log.info('Stopped Reconstructor Queue Watcher...')

def update_job_status(post_url=None, job_id=None, action=None, value=None, filename=None, version=None, download_key=None, file_size=None, log_filename=None):
    try:
        if not post_url:
            log.error('Cannot update job status: No post url...')
            return False
        values = {}
        if job_id:
            values['job_id'] = job_id
        if action:
            values['action'] = action
        if value:
            values['value'] = value
        if filename:
            values['filename'] = filename
        if version:
            values['version'] = version
        if download_key:
            values['download_key'] = download_key
        if file_size:
            values['file_size'] = file_size
        if log_filename:
            values['log_filename'] = log_filename
        values['repo_url'] = settings.REPO_DOWNLOAD_URL
        #log.debug('Updating job status: %s' % (values))
        data = urllib.urlencode(values)
        req = urllib2.Request(post_url, data)
        urllib2.urlopen(req) 
    except Exception, d:
        log.warning('Unable to update job status: %s', (d))
        # save file for debugging
        f = open('/tmp/reconstructor_error.html', 'w')
        f.write(d.read())
        f.close()
        pass


def main(engine=None, gui=None):
    try:
        # start engine
        # use engine instance if present -- otherwise try to create one from globals TODO: fix to only accept instance
        if engine:
            eng = engine
        else:
            eng = BuildEngine(distro=DISTRO_TYPE, arch=ARCH, working_dir=WORKING_DIR, src_iso_filename=SRC_ISO_FILE, project=PROJECT, lvm_name=LVM_NAME, output_file=OUTPUT_FILE, build_type=BUILD_TYPE)
        if BUILD_TYPE == 'live':
            # live project
            if eng.get_project() == None or eng.get_project().project_type == 'live':
                log.info('Building live disc...')
                log.info('Running live project...')
                prj_filename = None
                if ONLINE:
                    # check iso repo
                    check_iso_repo()
                    # update web app with status and server
                    prj = eng.get_project()
                    update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='status', value='building')
                    update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Starting...')
        
                # set project_dir for distro
                if PROJECT:
                    eng.get_distro().set_project_dir(eng.get_project().get_tmpdir())
        
                if not opts.lvm_name and eng.get_src_iso_filename():
                    # extract ISO if requested
                    if opts.skip_iso_extract == False:
                        eng.extract_iso()
                    else:
                        log.info('Skipping ISO extraction...')
                    # extract SquashFs if requested
                    if opts.skip_livefs_extract == False:
                        eng.extract_live_fs()
                    else:
                        log.info('Skipping LiveFS filesystem extraction...')
                    # extract initrd if requested
                    if opts.skip_initrd_extract == False:
                        eng.extract_initrd()
                    else:
                        log.info('Skipping Initrd extraction...')
                
                if PROJECT:
                    if ONLINE:
                        update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Setting up environment...')
                    # setup customization environment
                    eng.setup_environment()
                    # add packages
                    if ONLINE:
                        update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Installing packages...')
                    eng.add_packages()
                    # remove packages
                    if ONLINE:
                        update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Removing packages...')
                    eng.remove_packages()
                else:
                    eng.setup_environment()
                # add additional packages
                if PACKAGES:
                    eng.add_packages(PACKAGES)    
                # remove packages
                if REMOVE_PACKAGES:
                    eng.remove_packages(REMOVE_PACKAGES)
                # enable persistent
                if PERSISTENT_SIZE != None:
                    eng.enable_persistent(size=PERSISTENT_SIZE)
                # add custom app
                if CUSTOM_APP != None:
                    eng.add_tar_app(CUSTOM_APP, dest_dir='/opt')
                # extract project data into root
                if PROJECT:
                    if eng.get_project().project_type.lower() == 'live':
                        eng.add_project_data()
                # run modules
                if PROJECT:
                    log.debug('Running modules...')
                    if ONLINE:
                        update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Running modules...')
                    eng.run_modules()
                # run scripts
                if PROJECT:
                    log.debug('Running scripts...')
                    if ONLINE:
                        update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Running post-script...')
                    prj = eng.get_project()
                    eng.run_script(prj.get_post_script())
        
                # teardown customization environment
                eng.teardown_environment()
            
                # build initrd if requested
                if not opts.skip_initrd_create:
                    if eng.get_project() == None or eng.get_project().project_type == 'live':
                        if ONLINE:
                            update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Building initial ramdisk...')
                        eng.build_initrd()
        
                # update kernel
                eng.update_kernel()
    
                # build live fs if requested
                if opts.no_build == False:
                    if ONLINE:
                        update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Building image...')
                    eng.build_live_fs()
                else:
                    log.info('Skipping build of live filesystem...')
                # add custom preseed
                if PRESEED:
                    if os.path.exists(PRESEED):
                        log.info('Adding custom preseed...')
                        preseed_file = PRESEED.split('/')[-1]
                        shutil.copy(PRESEED, os.path.join(eng.get_iso_fs_dir(), 'preseed' + os.sep + preseed_file))
                    else:
                        log.error('Preseed file not found: %s' % (PRESEED))
                # build output
                if ONLINE or OUTPUT_FILE and not opts.skip_iso_create:
                    ptype = 'iso'
                    if PROJECT:
                        if eng.get_project().environment.strip().lower() == 'netbook':
                            ptype = 'netbook'
                    log.info('Building image...')
                    if ptype == 'netbook':
                        if ONLINE:
                            update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Building image...')
                        # TODO: finish build netbook image
                        self.log.error('Not implemented...')
                    elif ptype == 'iso':
                        log.info('Building ISO...')
                        if ONLINE:
                            update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Building ISO...')
                        if eng.create_iso():
                            log.info('ISO build complete.')
                            prj_filename = eng.get_output_filename()
                if ONLINE:
                    log.info('Final size: %s MB' % (os.path.getsize(os.path.join(settings.ONLINE_ISO_REPO, prj_filename)) / 1048576))
                else:
                    if prj_filename:
                        log.info('Final size: %s MB' % (os.path.getsize(prj_filename) / 1048576))
                # copy build log
                if ONLINE:
                    log_filename = '%s_%s.log' % (eng.get_project().name.replace(' ', '_'), eng.get_project().author.replace(' ', '_'))
                    shutil.copy(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'build.log'), os.path.join(settings.ONLINE_ISO_REPO, log_filename))
                log.info('Done.')
                # update UI if running
                if gui:
                    gui.build_complete()
                
                # post status if online
                if ONLINE:
                    prj = eng.get_project()
                    filename = None
                    # get size of project (in MB)
                    file_size = int(os.path.getsize(os.path.join(settings.ONLINE_ISO_REPO, prj_filename)) / 1048576)
                    #if settings.REPO_DOWNLOAD_URL.endswith('/'):
                    #    file_link = settings.REPO_DOWNLOAD_URL + prj_filename
                    #else:
                    #    file_link = settings.REPO_DOWNLOAD_URL + '/' + prj_filename
                    # only send filename -- downloads now handled with django
                    filename = prj_filename
    
                    update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='status', value='complete', filename=filename, version=prj.version, download_key=eng.get_download_key(), log_filename=log_filename, file_size=file_size)
                    update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Done')
    
            # ec2 project
            elif eng.get_project().project_type == 'ec2':
                if not ONLINE:
                    log.error('EC2 projects can only be run from the Reconstructor Build Service...')
                    sys.exit(1)
                log.info('Running EC2 project...')
                # check iso repo
                check_iso_repo()
                # update web app with status and server
                prj = eng.get_project()
                update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='status', value='building')
                update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Starting...')
    
                # set project_dir for distro
                eng.get_distro().set_project_dir(eng.get_project().get_tmpdir())
                
                # setup customization environment
                update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Setting up environment...')
                eng.setup_environment()
                # add packages
                update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Installing packages...')
                eng.add_packages()
                # remove packages
                update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Removing packages...')
                eng.remove_packages()
                # add public ssh credentials
                eng.add_ssh_credentials()
                
                log.debug('EC2 environment; running scripts...')
                update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Running post-script...')
                prj = eng.get_project()
                eng.run_script(prj.get_post_script())
        
                # build ami
                update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Building image...')
                prefix = eng.get_project().name.lower().replace(' ', '_')
                cert = os.path.join(eng.get_project().get_tmpdir(), 'files' + os.sep + eng.get_project().aws_cert)
                key = os.path.join(eng.get_project().get_tmpdir(), 'files' + os.sep + eng.get_project().aws_key)
                id = eng.get_project().aws_id
                s3_bucket = eng.get_project().aws_s3_bucket
                s3_id = eng.get_project().aws_s3_access_id
                s3_key = eng.get_project().aws_s3_access_key
    
                # build
                eng.build_ec2_ami(prefix=prefix, cert=cert, key=key, id=id)
                
                # upload
                update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Uploading...')
                eng.upload_ec2_ami(prefix=prefix, s3_id=s3_id, s3_key=s3_key, s3_bucket=s3_bucket)
    
                # teardown customization environment
                eng.teardown_environment()
    
                # copy build.log
                shutil.copy(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'build.log'), os.path.join(settings.ONLINE_ISO_REPO, '%s_%s.log' % (eng.get_project().name.replace(' ', '_'), eng.get_project().author.replace(' ', '_'))))
                # finish
                log.info('EC2 build complete.')
    
                # update job status
                prj = eng.get_project()
                update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='status', value='complete', verion=prj.version)
                update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Done')
    
            # disk image project
            elif eng.get_project().project_type == 'disk':
                log.info('Running disk image project...')
                prj_filename = None
                if ONLINE:
                    # check iso repo
                    check_iso_repo()
                    # update web app with status and server
                    prj = eng.get_project()
                    update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='status', value='building')
                    update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Starting...')
        
                # set project_dir for distro
                if PROJECT:
                    eng.get_distro().set_project_dir(eng.get_project().get_tmpdir())
        
                if not opts.lvm_name and eng.get_src_iso_filename():
                    # extract ISO if requested
                    if opts.skip_iso_extract == False:
                        eng.extract_iso()
                    else:
                        log.info('Skipping ISO extraction...')
                    # extract SquashFs if requested
                    if opts.skip_livefs_extract == False:
                        eng.extract_live_fs()
                    else:
                        log.info('Skipping Squash filesystem extraction...')
                    # extract initrd if requested
                    if opts.skip_initrd_extract == False:
                        eng.extract_initrd()
                    else:
                        log.info('Skipping Initrd extraction...')
                
                if PROJECT:
                    # setup customization environment
                    if ONLINE:
                        update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Setting up environment...')
                    eng.setup_environment()
                    # add packages
                    if ONLINE:
                        update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Installing packages...')
                    eng.add_packages()
                    if ONLINE:
                        update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Removing packages...')
                    eng.remove_packages()
                    # install grub if needed
                    ptype = eng.get_project().disk_image_type
                    if ptype == 'qemu' or ptype == 'vmware':
                        p = ['grub',]
                        eng.add_packages(packages=p)
                if PACKAGES:
                    eng.add_packages(PACKAGES)
                if REMOVE_PACKAGES:
                    eng.remove_packages(REMOVE_PACKAGES)
                # enable persistent
                if PERSISTENT_SIZE != None:
                    eng.enable_persistent(size=PERSISTENT_SIZE)
                # add custom app
                if CUSTOM_APP != None:
                    eng.add_tar_app(CUSTOM_APP, dest_dir='/opt')
                # extract project data into root
                if PROJECT:
                    eng.add_project_data()
                # run modules
                if PROJECT:
                    log.debug('Running modules...')
                    if ONLINE:
                        update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Running modules...')
                    eng.run_modules()
                # run scripts
                if PROJECT:
                    log.debug('Running scripts...')
                    if ONLINE:
                        update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Running post-script...')
                    prj = eng.get_project()
                    eng.run_script(prj.get_post_script())
        
                # teardown customization environment
                eng.teardown_environment()
            
                if prj:
                    if prj.online:
                        img = os.path.join(tempfile.gettempdir(), prj.name.replace(' ', '_') + '_' + prj.author.lower() + '.img')
                    else:
                        img = self.__output_file
                else:
                    img = self.__output_file
                # create
                img_size = '5'
                if prj.disk_image_size:
                    img_size = prj.disk_image_size
                
                # build live fs if requested
                if opts.no_build == False:
                    if ONLINE:
                        update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Building image...')
                    eng.build_live_fs()
                else:
                    log.info('Skipping build of live filesystem...')
    
                prj_filename = eng.create_disk_image(size=img_size, dest_file=img, image_type=prj.disk_image_type, distro_name=eng.get_project().distro)
                log.debug('Compressing image...')
                if ONLINE:
                    update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Compressing image...')
                os.system('gzip -f -2 %s' % (os.path.join(tempfile.gettempdir(), prj_filename)))
                prj_filename += '.gz'
                
                if ONLINE:
                    log.debug('Moving to online repo...')
                    if os.path.exists(os.path.join(settings.ONLINE_ISO_REPO, prj_filename)):
                        log.debug('Removing existing image...')
                        os.remove(os.path.join(settings.ONLINE_ISO_REPO, prj_filename))
                    shutil.move(os.path.join(tempfile.gettempdir(), prj_filename), os.path.join(settings.ONLINE_ISO_REPO, prj_filename))
                
                log.info('Done.')
    
                # copy build log
                if ONLINE:
                    log_filename = '%s_%s.log' % (eng.get_project().name.replace(' ', '_'), eng.get_project().author.replace(' ', '_'))
                    shutil.copy(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'build.log'), os.path.join(settings.ONLINE_ISO_REPO, log_filename))
                    
                # post status if online
                if ONLINE:
                    prj = eng.get_project()
                    filename = None
                    file_size = int(os.path.getsize(os.path.join(settings.ONLINE_ISO_REPO, prj_filename)) / 1048576)
                    #if settings.REPO_DOWNLOAD_URL.endswith('/'):
                    #    file_link = settings.REPO_DOWNLOAD_URL + prj_filename
                    #else:
                    #    file_link = settings.REPO_DOWNLOAD_URL + '/' + prj_filename
                    # only send filename - django handles downloads
                    filename = prj_filename
                    
                    log.debug('Project filename: %s' % (prj_filename))
                    log.debug('Filename: %s' % (filename))
                    update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='status', value='complete', filename=filename, version=prj.version, download_key=eng.get_download_key(), log_filename=log_filename, file_size=file_size)
                    update_job_status(post_url=prj.job_status_post_url, job_id=prj.job_id, action='build_action', value='Done')
                log.info('Build complete...')
                if gui:
                    gui.send_stats()
        elif BUILD_TYPE == 'alternate':
            # build alternate (install) disc
            log.info('Building alternate (install) disc...')
            # extract
            if opts.skip_iso_extract == False:
                eng.extract_iso()
            # packages -- call even if no packages were specified on command line in case they were added manually
            eng.add_packages(PACKAGES)    
            # add custom preseed
            if PRESEED:
                if os.path.exists(PRESEED):
                    log.info('Adding custom preseed: %s' % (PRESEED))
                    preseed_file = PRESEED.split('/')[-1]
                    shutil.copy(PRESEED, os.path.join(eng.get_iso_fs_dir(), 'preseed' + os.sep + preseed_file))
                else:
                    log.error('Preseed file not found: %s' % (PRESEED))
            # build
            if not OUTPUT_FILE:
                log.info('No output file specified; not creating ISO...')
            elif OUTPUT_FILE and not opts.skip_iso_create:
                if eng.create_iso():
                    log.info('ISO build complete.')
                    prj_filename = eng.get_output_filename()
        else:
            log.error('Unknown build type: %s' % (build_type))

    except Exception, d:
        log.error(d)
        # post status if online
        if ONLINE:
            prj = eng.get_project()
            # copy build log
            log_filename = '%s_%s.log' % (eng.get_project().name.replace(' ', '_'), eng.get_project().author.replace(' ', '_'))
            shutil.copy(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'build.log'), os.path.join(settings.ONLINE_ISO_REPO, log_filename))
            update_job_status(post_url=prj.job_status_post_url, log_filename=log_filename, job_id=prj.job_id, action='status', value='error')
    finally:
        # cleanup
        if PROJECT:
            eng.get_project().cleanup()

        if opts.lvm_name or ONLINE:
            # unmount working directory
            log.debug('Unmounting %s' % (WORKING_DIR))
            os.system('umount %s' % (WORKING_DIR))
            if opts.keep_lvm:
                log.info('LVM volume available at %s...' % (os.path.join(settings.LVM_ROOT, WORKING_DIR.split('/')[-1])))
            else:
                # remove lvm snapshot
                log.info('Removing temporary LVM volume...')
                os.system('lvremove -f %s' % (os.path.join(settings.LVM_ROOT, WORKING_DIR.split('/')[-1])))
            # remove temp lvm dir
            shutil.rmtree(WORKING_DIR)
        # update UI if needed
        if gui:
            gui.build_complete()
        
class BuildEngine(object):
    '''Master Reconstructor Build Engine'''
    def __init__(self, distro=None, arch=None, description=None, working_dir=None, src_iso_filename=None, project=None, lvm_name=None, output_file=None, build_type=None):
        # configure logging
        self.log = logging.getLogger('BuildEngine')
        #self.log.debug('%s, %s, %s, %s, %s, %s, %s, %s' % (distro, arch, description, working_dir, src_iso_filename, project, lvm_name, output_file))
        self.log.debug('Engine initialized...')
        self.__all_distros = ['ubuntu','centos','debian',]
        self.__arch = arch
        self.__distro_name = distro.lower()
        self.log.debug('Distro: %s Arch: %s' % (self.__distro_name, self.__arch))
        self.__output_file = output_file
        self.__build_type = build_type
        if description:
            self.__description = description
        else:
            self.__description = '%s custom' % (self.__distro_name)
        self.__project = project
        self.__lvm_name = lvm_name
        self.__distro = None
        self.__working_dir = working_dir
        self.__run_post_config = None
        # generate keys
        #t = datetime.date.today()
        #hash = int(t.month + t.day + t.year)
        #seed = t.month * t.day
        chars = string.letters + string.digits
        download_key = ''.join(Random().sample(chars, 16))
        log_key = ''.join(Random().sample(chars, 16))
        self.__download_key = download_key
        self.__log_key = log_key
        #self.log.debug('Download Key: %s  Log Key: %s' % (download_key, log_key))
        # load
        if self.__project:
            self.load_distro(arch=self.__arch, distro_name=self.__distro_name, working_dir=self.__working_dir, src_iso_filename=src_iso_filename, build_type=self.__build_type)
            self.__description = self.__project.name
            self.__run_post_config = self.__project.run_post_config
        else:
            self.load_distro(arch=self.__arch, distro_name=distro, working_dir=self.__working_dir, src_iso_filename=src_iso_filename, build_type=self.__build_type)
            self.__run_post_config = False
    
    # accessors
    def get_work_dir(self): return self.__distro.get_work_dir()
    def set_arch(self, value): self.__arch == value
    def get_src_iso_filename(self): return self.__distro.get_src_iso_filename()
    def get_live_fs_dir(self): return self.__distro.get_live_fs_dir()
    def get_live_fs_filename(self): return self.__distro.get_live_fs_filename()
    def get_iso_fs_dir(self): return self.__distro.get_iso_fs_dir()
    def get_output_filename(self): return self.__output_file
    def get_project(self): return self.__project
    def set_project(self, value): self.__project = value
    def get_distro(self): return self.__distro
    def get_download_key(self): return self.__download_key
    def get_log_key(self): return self.__log_key
    
    def load_distro(self, arch=None, distro_name=None, working_dir=None, src_iso_filename=None, build_type=None):
        if distro_name.strip().lower() not in self.__all_distros:
            self.log.error('Distribution %s not valid. Available distros: %s' % (distro_name, self.__all_distros))
            sys.exit(1)
        else:
            # load distro
            if PROJECT:
                ptype = PROJECT.project_type
                if ptype == 'live' or ptype == 'disk':
                    self.log.debug('Loading Live project...')
                    if distro_name == 'ubuntu':
                        self.__distro = ubuntu.UbuntuDistro(arch=arch, working_dir=working_dir, src_iso_filename=src_iso_filename, online=self.__project.online, run_post_config=self.__run_post_config, mksquashfs=MKSQUASHFS, unsquashfs=UNSQUASHFS, build_type=build_type)
                    elif distro_name == 'centos':
                        self.__distro = centos.CentosDistro(arch=arch, working_dir=working_dir, src_iso_filename=src_iso_filename, online=self.__project.online, run_post_config=self.__run_post_config, mksquashfs=MKSQUASHFS, unsquashfs=UNSQUASHFS, build_type=build_type)
                    elif distro_name == 'debian':
                        self.__distro = debian.DebianDistro(arch=arch, working_dir=working_dir, src_iso_filename=src_iso_filename, online=self.__project.online, run_post_config=self.__run_post_config, mksquashfs=MKSQUASHFS, unsquashfs=UNSQUASHFS, build_type=build_type)
                    else:
                        self.log.error('Unknown distro for live or disk project...')
                        sys.exit(1)
                elif ptype == 'ec2':
                    self.log.debug('Loading EC2 project...')
                    # TODO: load ec2 distro type
                    if distro_name == 'ubuntu':
                        self.__distro = ubuntu_ec2.UbuntuEC2Distro(arch=arch, working_dir=working_dir)
                    else:
                        self.log.error('Unknown distro for EC2 project...')
                        sys.exit(1)
            else:
                if distro_name == 'ubuntu':
                    self.__distro = ubuntu.UbuntuDistro(arch=arch, working_dir=working_dir, src_iso_filename=src_iso_filename, online=False, run_post_config=self.__run_post_config, mksquashfs=MKSQUASHFS, unsquashfs=UNSQUASHFS, build_type=build_type)
                elif distro_name == 'centos':
                    self.__distro = centos.CentosDistro(arch=arch, working_dir=working_dir, src_iso_filename=src_iso_filename, online=False, run_post_config=self.__run_post_config, mksquashfs=MKSQUASHFS, unsquashfs=UNSQUASHFS, build_type=build_type)
                elif distro_name == 'debian':
                    self.__distro = debian.DebianDistro(arch=arch, working_dir=working_dir, src_iso_filename=src_iso_filename, online=False, run_post_config=self.__run_post_config, mksquashfs=MKSQUASHFS, unsquashfs=UNSQUASHFS, build_type=build_type)

            self.log.info('Build Distribution: %s' % (distro_name))
     
    def extract_iso(self):
        self.log.info('Extracting ISO...  Please wait...')
        return self.__distro.extract_iso_fs()
        
    def extract_live_fs(self):
        self.log.info('Extracting Live filesystem... Please wait...')
        # check squashfs tools
        mk_s = commands.getoutput('%s -version' % (MKSQUASHFS))
        un_s = commands.getoutput('%s -version' % (UNSQUASHFS))
        mk_ver = Decimal(mk_s.split('\n')[0].split(None, 4)[2])
        un_ver = Decimal(un_s.split('\n')[0].split(None, 4)[2])
        # check
        if DISTRO_TYPE == 'ubuntu':
            self.log.info('You must have SquashFS tools 3.3+ for Ubuntu 9.04 and 4.0+ for Ubuntu 9.10+...')
        elif DISTRO_TYPE == 'centos':
            self.log.info('You must have SquashFS tools 3.4 for CentOS 5.4...')
        return self.__distro.extract_live_fs()
    
    def create_disk_image(self, size='10', dest_file=None, image_type=None, distro_name=''):
        self.log.info('Creating disk image... Please wait...')
        return self.__distro.create_disk_image(size=size, dest_file=dest_file, image_type=image_type, distro_name=distro_name)

    def extract_initrd(self):
        self.log.info('Extracting Initrd...  Please wait...')
        return self.__distro.extract_initrd()

    def build_live_fs(self):
        self.log.info('Building Live filesystem... Please wait...')
        return self.__distro.build_live_fs()

    def build_initrd(self):
        self.log.info('Building Initrd...  Please wait...')
        return self.__distro.build_initrd()

    def update_kernel(self):
        self.log.info('Updating Kernel... Please wait...')
        return self.__distro.update_boot_kernel()
    
    def add_ssh_credentials(self):
        return self.__distro.add_public_ssh_credentials()

    def build_ec2_ami(self, prefix=None, cert=None, key=None, id=None):
        self.log.info('Building EC2 AMI... Please wait...')
        return self.__distro.build_ec2_ami(prefix=prefix, cert=cert, key=key, id=id)
    
    def upload_ec2_ami(self, prefix=None, s3_id=None, s3_key=None, s3_bucket=None):
        self.log.info('Uploading EC2 AMI... Please wait...')
        return self.__distro.upload_ec2_ami(prefix=prefix, s3_id=s3_id, s3_key=s3_key, s3_bucket=s3_bucket)

    def add_tar_app(self, source_filename=None, dest_dir=None):
        self.log.info('Adding application %s' % (source_filename))
        return self.__distro.extract_tar_application(source_filename=source_filename, dest_dir=dest_dir)
            
    def add_to_target(self, src=None, dest=None, overwrite=False):
        self.log.info('Adding %s to target filesystem...' % (src))
        raise RuntimeError, "Not yet implemented..."

    def add_packages(self, packages=None):
        if self.__project:
                return self.__distro.add_packages(packages=self.__project.packages)
        else:
            if packages == None:
                packages = []
            return self.__distro.add_packages(packages=packages)

    def remove_packages(self, packages=None):
        if self.__project:
                return self.__distro.remove_packages(packages=self.__project.base_packages_removed)
        else:
            if packages == None:
                packages = []
            return self.__distro.remove_packages(packages=packages)

    def run_modules(self):
        try:
            self.log.info('Running modules...')
            return self.__distro.run_modules(self.__project.modules)
        except Exception, d:
            self.log.error('Error running modules: %s' % (d))
            return False

    def run_script(self, script_file=None):
        self.log.info('Running script: %s' % (script_file))
        return self.__distro.run_script(script_file)

    def set_gconf_value(self, key=None, key_type=None, value=None):
        return self.__distro.set_gconf_value(key=key, key_type=key_type, value=value)

    def add_project_data(self):
        self.log.info('Adding project data...')
        if self.__project:
            data_file = os.path.join(self.__project.get_tmpdir(), 'data.tar.gz')
            if os.path.exists(data_file):
                t = tarfile.open(data_file)
                t.extractall(self.get_live_fs_dir())
                return True
            else:
                self.log.warning('No data archive...')
                return False
        else:
            self.log.error('No project data...')
            return False

    def create_iso(self):
        # add 'made with' id
        #self.log.debug('Adding Disc ID...')
        f = open(os.path.join(self.__distro.get_iso_fs_dir(), '.r_id'), 'w')
        f.write('Built using %s %s\n%s\n%s\n' % (settings.APP_NAME, settings.APP_VERSION, settings.APP_COPYRIGHT, settings.APP_URL))
        f.close()
        if self.__project:
            if self.__project.online:
                # write to file for online version
                self.__output_file = self.__project.name.replace(' ', '_') + '_' + self.__project.author.replace(' ', '_') + '.iso'
                return iso_tools.create(description=self.__description, src_dir=self.__distro.get_iso_fs_dir(), dest_file=os.path.join(settings.ONLINE_ISO_REPO, self.__output_file))
            else:
                return iso_tools.create(description=self.__description, src_dir=self.__distro.get_iso_fs_dir(), dest_file=self.__output_file)
        else:
            return iso_tools.create(description=self.__description, src_dir=self.__distro.get_iso_fs_dir(), dest_file=self.__output_file)
    
    def enable_persistent(self, size=64):
        if self.__distro_name == 'ubuntu':
            return self.__distro.enable_persistent_fs(size)
        else:
            self.log.error('Persistent filesystem only supported on Ubuntu...')
            return False
                    
    def setup_environment(self):
        try:
            self.log.info('Setting up environment for customization...')
            # copy dns info
            self.log.debug('Copying DNS configuration...')
            shutil.copy('/etc/resolv.conf', os.path.join(self.__distro.get_live_fs_dir(), 'etc'+os.sep+'resolv.conf'))
            # copy /etc/hosts
            shutil.copy('/etc/hosts', os.path.join(self.__distro.get_live_fs_dir(), 'etc'+os.sep+'hosts'))
            # mount /proc
            fs_tools.bind_mount('/proc', os.path.join(self.__distro.get_live_fs_dir(), 'proc'))
            # prevent package manager from starting daemons
            if self.__distro_name == 'ubuntu' or self.__distro_name == 'debian':
                self.log.debug('Setting up daemon startup configuration...')
                policy_file = os.path.join(self.__distro.get_live_fs_dir(), 'usr' + os.sep + 'sbin' + os.sep + 'policy-rc.d')
                f = open(policy_file, 'w')
                f.write('#!/bin/sh\nexit 101\n')
                f.close()
                # make executable
                os.chmod(policy_file, 0775)
                
            # mount /dev/pts if ubuntu
            if self.__distro_name == 'ubuntu':
                fs_tools.bind_mount('/dev/pts', os.path.join(self.__distro.get_live_fs_dir(), 'dev' + os.sep + 'pts'))
        except Exception, d:
            self.log.error('Error setting up environment: %s' % (d))

    def teardown_environment(self):
        try:
            self.log.info('Tearing down customization environment...')
            self.log.debug('Restoring DNS configuration...')
            if os.path.exists(os.path.join(self.__distro.get_live_fs_dir(), 'etc'+os.sep+'resolv.conf')):
                os.remove(os.path.join(self.__distro.get_live_fs_dir(), 'etc'+os.sep+'resolv.conf'))
            if os.path.exists(os.path.join(self.__distro.get_live_fs_dir(), 'etc'+os.sep+'hosts')):
                os.remove(os.path.join(self.__distro.get_live_fs_dir(), 'etc'+os.sep+'hosts'))
            # unmount /proc
            self.log.debug('Unmounting /proc')
            fs_tools.unmount_bind(os.path.join(self.__distro.get_live_fs_dir(), 'proc'))
            fs_tools.unmount_bind(os.path.join(self.__distro.get_live_fs_dir(), 'dev' + os.sep + 'pts'))
            # remove config for preventing daemons from starting
            if self.__distro_name == 'ubuntu' or self.__distro_name == 'debian':
                self.log.debug('Removing daemon configuration...')
                os.remove(os.path.join(self.__distro.get_live_fs_dir(), 'usr' + os.sep + 'sbin' + os.sep + 'policy-rc.d'))
            # unmount anything left
            self.log.debug('Unmounting any left over mounts...')
            # remove project dir if needed
            if PROJECT and os.path.exists(self.__distro.get_project_dir()):
                self.log.debug('Removing temporary project dir...')
                shutil.rmtree(self.__distro.get_project_dir())
            # get all current mounts
            f = open('/proc/mounts', 'r')
            mounts = f.read().split('\n')
            # reverse list to unmount last first
            mounts.reverse()
            # loop through and unmount
            for m in mounts:
                # only look for temporary LVM volume mount
                if m != '' and m.find(self.__working_dir) > -1:
                    # don't unmount live fs dir
                    if m.split()[1].strip() != self.__working_dir:
                        self.log.debug('Unmounting %s...' % (m.split(' ')[1]))
                        os.system('umount -f %s' % (m.split(' ')[1]))

        except Exception, d:
            import traceback
            traceback.print_exc()
            self.log.error('Error tearing down environment: %s' % (d))


class ReconstructorGui(object):
    def __init__(self):
        self.ui_filename = os.path.join(os.path.join(os.getcwd(), 'ui'), 'reconstructor.ui')
        builder = gtk.Builder()
        builder.add_from_file(self.ui_filename)
        self.main_window = builder.get_object('window_main')
        self.main_window.set_title('%s' % (settings.APP_NAME))
        self.textview_log = builder.get_object('textview_log')
        self.filechooser_project = builder.get_object('filechooserbutton_project_filename')
        self.filechooser_project.set_current_folder(os.environ['HOME'])
        self.filechooser_src_iso = builder.get_object('filechooserbutton_src_iso_filename')
        self.filechooser_src_iso.set_current_folder(os.environ['HOME'])
        self.filechooser_working_dir = builder.get_object('filechooserbutton_working_dir')
        self.filechooser_working_dir.set_current_folder(os.environ['HOME'])
        self.label_target_filename = builder.get_object('label_target_filename')
        self.toolbutton_build = builder.get_object('toolbutton_build')
        self.toolbutton_help = builder.get_object('toolbutton_help')
        self.checkbox_skip_iso_extract = builder.get_object('checkbutton_skip_iso_extract')
        self.checkbox_skip_livefs_extract = builder.get_object('checkbutton_skip_livefs_extract')
        self.checkbox_skip_initrd_extract = builder.get_object('checkbutton_skip_initrd_extract')
        self.checkbox_skip_iso_create = builder.get_object('checkbutton_skip_iso_create')
        self.checkbox_skip_livefs_create = builder.get_object('checkbutton_skip_livefs_create')
        self.checkbox_skip_initrd_create = builder.get_object('checkbutton_skip_initrd_create')
        self.checkbox_keep_working_dir = builder.get_object('checkbutton_keep_working_dir')
        self.scrolledwindow_log = builder.get_object('scrolledwindow_log')
        # create temp working dir by default
        self.tmpdir = tempfile.mkdtemp()
        WORKING_DIR = self.tmpdir
        self.filechooser_working_dir.set_filename(self.tmpdir)
        # create the textbuffer for the textview
        self.textbuffer_log = gtk.TextBuffer(None)
        self.textview_log.set_buffer(self.textbuffer_log)
        # create filefilters for file choosers
        # filter for .rpj
        filter_project = gtk.FileFilter()
        filter_project.set_name("Reconstructor Project Bundle")
        filter_project.add_pattern("*.rpj")
        self.filechooser_project.set_filter(filter_project)
        # filter for .iso
        filter_iso = gtk.FileFilter()
        filter_iso.set_name("Image Files (.iso)")
        filter_iso.add_pattern("*.iso")
        self.filechooser_src_iso.set_filter(filter_iso)
        # connect signals
        builder.connect_signals(self)
        self.scrolledwindow_log.get_vadjustment().connect('changed', lambda a, s=self.scrolledwindow_log: self.on_scroll_changed(a,s))
        # show window
        self.main_window.show()
    
    def get_textbuffer(self): return self.textbuffer_log

    def add_log_entry(self, text):
        if self.textbuffer_log.get_char_count() > 0:
            txt = self.textbuffer_log.get_text()
        else:
            txt = ''
        self.textbuffer_log.set_text(txt + '\n' + text)

    def build(self):
        # check values
        project_filename = self.filechooser_project.get_filename()
        if project_filename == None or not os.path.exists(project_filename):
            log.error('You must select a valid project...')
            return False
        src_iso_filename = self.filechooser_src_iso.get_filename()
        if src_iso_filename == None or not os.path.exists(src_iso_filename):
            log.error('You must select a valid source ISO...')
            return False
        target_filename = self.label_target_filename.get_text()
        if target_filename == '':
            log.error('You must select a target output filename...')
            return False
        working_dir = self.filechooser_working_dir.get_filename()
        if working_dir == None or not os.path.exists(working_dir):
            log.error('You must select a valid working directory...')
            return False
        # get advanced values
        skip_iso_extract = self.checkbox_skip_iso_extract.get_active()
        skip_livefs_extract = self.checkbox_skip_livefs_extract.get_active()
        skip_initrd_extract = self.checkbox_skip_initrd_extract.get_active()
        skip_iso_create = self.checkbox_skip_iso_create.get_active()
        skip_livefs_create = self.checkbox_skip_livefs_create.get_active()
        skip_initrd_create = self.checkbox_skip_initrd_create.get_active()
        if skip_iso_extract:
            log.info('Skipping ISO extraction...')
            opts.skip_iso_extract = True
        else:
            opts.skip_iso_extract = False
        if skip_livefs_extract:
            log.info('Skipping LiveFS extraction...')
            opts.skip_livefs_extract = True
        else:
            opts.skip_livefs_extract = False
        if skip_initrd_extract:
            log.info('Skipping Initrd extraction...')
            opts.skip_initrd_extract = True
        else:
            opts.skip_initrd_extract = False
        if skip_iso_create:
            log.info('Skipping ISO creation...')
            opts.skip_iso_create = True
        else:
            opts.skip_iso_create = False
        if skip_livefs_create:
            log.info('Skipping LiveFS creation...')
            opts.no_build = True
        else:
            opts.no_build = False
        if skip_initrd_create:
            log.info('Skipping Initrd creation...')
            opts.skip_initrd_create = True
        else:
            opts.skip_initrd_create = False
        # build
        PROJECT = Project(project_filename)
        DISTRO_TYPE = PROJECT.distro
        ARCH = PROJECT.arch
        OUTPUT_FILE = target_filename
        WORKING_DIR = working_dir
            
        # set squashfs-tools
        ver = PROJECT.distro_version.strip()
        squash_version = commands.getoutput('mksquashfs -version').split('\n')[0]
        if squash_version.find('3.3') > -1:
            squash_version = Decimal('3.3')
        elif squash_version.find('4.0') > -1:
            squash_version = Decimal('4.0')
        MKSQUASHFS = commands.getoutput('which mksquashfs')
        UNSQUASHFS = commands.getoutput('which unsquashfs')
        # HACK: set globals for engine
        globals()['PROJECT'] = PROJECT
        globals()['DISTRO_TYPE'] = DISTRO_TYPE
        globals()['ARCH'] = ARCH
        globals()['OUTPUT_FILE'] = OUTPUT_FILE
        globals()['WORKINGDIR'] = WORKING_DIR
        globals()['MKSQUASHFS'] = MKSQUASHFS
        globals()['UNSQUASHFS'] = UNSQUASHFS
        # check squash for compatibility
        if ver == '9.04' and squash_version < Decimal('3.3'):
            log.error('You need to upgrade your SquashFS tools before preceding...')
            return False
        if ver == '9.10' or ver == '10.04' and squash_version < Decimal('4.0'):
            log.error('You need to upgrade your SquashFS tools before preceding...')
            return False
        else:
            if ver != '9.04' and ver != '9.10' or ver != '10.04':
                log.warn('Unknown distro version (%s).  Using system default squashfs-tools...' % (ver))
        # check for ec2
        PROJECT_TYPE = PROJECT.project_type.strip().lower()
        if PROJECT_TYPE == 'ec2':
            log.error('You cannot build EC2 projects with the standalone engine...')
            return False
        # start
        log.info('Starting Engine...')
        # update windows (set busy)
        self.main_window.set_title(settings.APP_NAME + ' (building...)')
        cursor = gtk.gdk.Cursor(gtk.gdk.WATCH)
        self.main_window.window.set_cursor(cursor)
        log.debug(WORKING_DIR)
        eng = BuildEngine(distro=DISTRO_TYPE, arch=ARCH, working_dir=WORKING_DIR, src_iso_filename=src_iso_filename, project=PROJECT, output_file=target_filename)
        # start engine in new thread to unblock UI
        threading.Thread(target=main, args=[eng,self]).start()
        return True

    def send_stats(self):
        try:
            params = urllib.urlencode({
                'engine_author': settings.APP_AUTHOR,
                'engine_name': settings.APP_NAME,
                'engine_site_url': settings.SITE_URL,
                'engine_version': settings.APP_VERSION,
                'engine_dev_rev': settings.APP_DEV_REV,
                'os_arch': platform.machine(),
                'python_version': platform.python_version(),
                'os_release': platform.release(),
                'os_lang': os.environ['LANG'],
                'os_distro': platform.dist()[0],
                'os_version': platform.dist()[1],
                'os_id': platform.dist()[2],
                'project_name': self.filechooser_project.get_filename().split(os.sep)[-1],
                })
            headers = {'Content-type': 'application/x-www-form-urlencoded', 'Accept': 'text/plain'}
            #srv = settings.APP_URL.split('//')[-1]
            srv = 'build.reconstructor.org'
            # use HTTPConnection for non SSL urls...
            conn = httplib.HTTPSConnection(srv)
            conn.request('POST', '/enginestat/', params, headers)
            conn.close()
        except Exception, d:
            #print(d)
            # ignore errors
            pass

    def build_complete(self):
        # reset UI
        self.main_window.set_title(settings.APP_NAME)
        self.main_window.window.set_cursor(None)

    def cleanup(self):
        # check for option to keep dir
        if not self.checkbox_keep_working_dir.get_active():
            # clean up tempdir in background -- could be huge and would block
            log.info('Cleaning up...')
            subprocess.Popen('rm -rf %s' % (self.tmpdir), shell=True)

    def quit(self, widget, data=None):
        self.cleanup()
        self.destroy()

    def on_button_target_filename_clicked(self, widget, data=None):
        chooser_save = gtk.FileChooserDialog(title='Target filename',action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
        chooser_save.set_current_folder(os.environ['HOME'])
        resp = chooser_save.run()
        if resp == gtk.RESPONSE_OK:
            self.label_target_filename.set_text(chooser_save.get_filename())
        chooser_save.destroy()
    
    def on_scroll_changed(self, adj, scroll):
        # scroll to bottom of window
        adj.set_value(adj.upper-adj.page_size)
        scroll.set_vadjustment(adj)

    def on_toolbutton_build_clicked(self, widget, data=None):
        #TODO: update textbuffer with streaming log info...
        self.build()

    def on_toolbutton_help_clicked(self, widget, data=None):
        # open a new tab in the default browser to the UserGuide
        webbrowser.open_new_tab(settings.HELP_URL)

    def on_button_chroot_clicked(self, widget, data=None):
        working_dir = self.filechooser_working_dir.get_filename()
        if not os.path.exists(os.path.join(working_dir, 'live_fs')):
            log.error('You must extract the ISO first...')
            return
        try:
            # setup environment
            # copy dns info
            log.debug("Copying DNS info...")
            shutil.copy('/etc/resolv.conf', os.path.join(working_dir, 'live_fs/etc/resolv.conf'))
            #os.system('cp -f /etc/resolv.conf ' + os.path.join(working_dir, "live_fs/etc/resolv.conf"))
            # mount /proc
            log.debug("Mounting /proc filesystem...")
            os.system('mount --bind /proc \"' + os.path.join(working_dir, "live_fs/proc") + '\"')
            # copy apt.conf
            log.debug("Copying apt configuration...")
            if not os.path.exists(os.path.join(working_dir, "live_fs/etc/apt/apt.conf.d/")):
                os.makedirs(os.path.join(working_dir, "live_fs/etc/apt/apt.conf.d/"))

            #shutil.copy2('/etc/apt/apt.conf.d/', os.path.join(working_dir, 'live_fs/etc/apt/apt/conf.d/'))
            os.system('cp -f /etc/apt/apt.conf.d/* ' + os.path.join(working_dir, "live_fs/etc/apt/apt.conf.d/"))
            # copy wgetrc
            log.debug("Copying wgetrc configuration...")
            # backup
            if os.path.exists('/etc/wgetrc'):
                try:
                    shutil.copy(os.path.join(working_dir, 'live_fs/etc/wgetrc'), os.path.join(working_dir, 'live_fs/etc/wgetrc.orig'))
                except:
                    pass
            #os.system('mv -f \"' + os.path.join(working_dir, "live_fs/etc/wgetrc") + '\" \"' + os.path.join(working_dir, "live_fs/etc/wgetrc.orig") + '\"')
                shutil.copy('/etc/wgetrc', os.path.join(working_dir, 'live_fs/etc/wgetrc'))
            #os.system('cp -f /etc/wgetrc ' + os.path.join(working_dir, "live_fs/etc/wgetrc"))
            # HACK: create temporary script for chrooting
            scr = '#!/bin/sh\n#\n#\t(c) Lumentica, 2010\n#\nchroot ' + os.path.join(working_dir, "live_fs/") + '\n'
            f=open('/tmp/reconstructor-terminal.sh', 'w')
            f.write(scr)
            f.close()
            os.chmod('/tmp/reconstructor-terminal.sh', 0775)
            #os.system('chmod a+x ' + os.path.join(working_dir, "/tmp/reconstructor-terminal.sh"))
            # TODO: replace default terminal title with "Reconstructor Terminal"
            # use gnome-terminal if available -- more features
            if commands.getoutput('which gnome-terminal') != '':
                log.info('Launching terminal for advanced customization...')
                os.system('export HOME=/root ; gnome-terminal --hide-menubar -t \"Reconstructor Terminal\" -e \"/tmp/reconstructor-terminal.sh\"')
            else:
                log.info('Launching terminal for advanced customization...')
                # use xterm if gnome-terminal isn't available
                os.system('export HOME=/root ; xterm -bg black -fg white -rightbar -title \"Reconstructor Terminal\" -e /tmp/reconstructor-terminal.sh')

            # restore wgetrc
            log.debug("Restoring wgetrc configuration...")
            try:
                shutil.move(os.path.join(working_dir, 'live_fs/etc/wgetrc.orig'), os.path.join(working_dir, 'live_fs/etc/wgetrc'))
            except:
                pass
            #os.system('mv -f \"' + os.path.join(working_dir, "live_fs/etc/wgetrc.orig") + '\" \"' + os.path.join(working_dir, "live_fs/etc/wgetrc") + '\"')
            # remove apt.conf
            #log.info("Removing apt.conf configuration...")
            #os.popen('rm -Rf \"' + os.path.join(self.customDir, "root/etc/apt/apt.conf") + '\"')
            # remove dns info
            log.debug("Removing DNS info...")
            os.remove(os.path.join(working_dir, 'live_fs/etc/resolv.conf'))
            #os.system('rm -Rf \"' + os.path.join(working_dir, "live_fs/etc/resolv.conf") + '\"')
            # umount /proc
            log.debug("Umounting /proc...")
            os.system('umount \"' + os.path.join(working_dir, 'live_fs/proc/') + '\"')
            # remove temp script
            os.remove('/tmp/reconstructor-terminal.sh')
        except Exception, detail:
            # restore settings
            # restore wgetrc
            log.debug("Restoring wgetrc configuration...")
            if os.path.exists(os.path.join(working_dir, 'live_fs/etc/wgetrc.orig')):
                shutil.move(os.path.join(working_dir, 'live_fs/etc/wgetrc.orig'), os.path.join(working_dir, 'live_fs/etc/wgetrc'))
            #os.system('mv -f \"' + os.path.join(working_dir, "live_fs/etc/wgetrc.orig") + '\" \"' + os.path.join(working_dir, "live_fs/etc/wgetrc") + '\"')
            # remove apt.conf
            #log.info("Removing apt.conf configuration...")
            #os.popen('rm -Rf \"' + os.path.join(self.customDir, "root/etc/apt/apt.conf") + '\"')
            # remove dns info
            log.debug("Removing DNS info...")
            os.remove(os.path.join(working_dir, "live_fs/etc/resolv.conf"))
            # umount /proc
            log.debug("Umounting /proc...")
            os.system('umount \"' + os.path.join(working_dir, "live_fs/proc/") + '\"')
            # remove temp script
            os.system('/tmp/reconstructor-terminal.sh')


    def on_destroy(self, widget, data=None):
        self.cleanup()
        gtk.main_quit()

def launch_gui():
    gtk.gdk.threads_init()
    r = ReconstructorGui()
    # setup log handler for GUI
    tb_log = TextBufferHandler(textbuffer=r.get_textbuffer())
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    tb_log.setFormatter(formatter)
    tb_log.setLevel(logging.INFO)
    logging.getLogger('').addHandler(tb_log)
    log.info('%s\n' % (settings.APP_COPYRIGHT))
    # call check_depends again to show in GUI
    deps = check_depends()
    if deps != '':
        log.warning('Please install the following dependencies: %s - Reconstructor will not work properly without them...' % (deps))
    # start app
    gtk.main()

# main
if __name__ == '__main__':
    print('\n%s (c) %s, 2010  %s\n' % ('Reconstructor Engine', 'Lumentica', 'http://www.lumentica.com'))
    PROJECT = None
    DISTRO_TYPE=None
    ARCH=None
    DESCRIPTION=None
    WORKING_DIR=os.path.join(os.environ['HOME'], 'reconstructor')
    SRC_ISO_FILE=None
    TARGET_DEV=None
    JAVA_RUNTIME=None
    CUSTOM_APP=None
    PERSISTENT_SIZE=None
    LVM_NAME=None
    OUTPUT_FILE=None
    ONLINE=False
    MKSQUASHFS=None
    UNSQUASHFS=None
    PACKAGES=None
    REMOVE_PACKAGES=None
    # cli options
    op = OptionParser()
    op.add_option('-g', '--gui', dest='launch_gui', action="store_true", default=False, help='Start the Reconstructor Engine GUI')
    op.add_option('-f', '--project-file', dest='project_file', help='Load project from file')
    op.add_option('-a', '--arch', dest='arch', help='Architecture for build (x86 or x86_64)')
    op.add_option('-d', '--distro', dest='distro_type', help='Distribution to use for build')
    op.add_option('-w', '--working-dir', dest='working_dir', help='Working directory')
    op.add_option('-i', '--iso-filename', dest='iso_filename', help='Source Ubuntu ISO filename')
    op.add_option('-v', '--description', dest='description', help='ISO description')
    op.add_option('-l', '--lvm', dest='lvm_name', help='Use LVM device as source')
    op.add_option('--build-type', dest='build_type', default='live', help='Type of distro to build; e.g. live, alternate')
    op.add_option('--add-packages', dest='add_packages', help='Comma separated list of additional packages to add to distro')
    op.add_option('--remove-packages', dest='remove_packages', help='Comma separated list of packages to remove from live distro')
    op.add_option('--queue', dest='queue', action="store_true", default=False, help='Start Reconstructor Queue watcher for online jobs')
    op.add_option('--keep-lvm', dest='keep_lvm', action="store_true", default=False, help='Do not remove temporary LVM volume')
    op.add_option('--install-only', dest='install_only', action="store_true", default=False, help='Skip extraction and build; Do install only')
    op.add_option('-b', '--build-only', dest='build_only', action="store_true", default=False, help='Bypass extraction and start build')
    #op.add_option('-t', '--target-device', dest='target_device', help='Target destination device')
    op.add_option('--no-confirm', dest='no_confirm', action="store_true", default=False, help='Bypass user confirmation for extraction, installation, etc. (for scripting...)')
    #op.add_option('-j', '--java-runtime', dest='java_runtime', help='Extract specified Java Runtime')
    op.add_option('-c', '--custom-app', dest='custom_app', help='Install specified custom application')
    op.add_option('-p', '--persistent-size', dest='persistent_size', help='Create persistent filesystem (in MB)')
    op.add_option('--skip-iso-extract', dest='skip_iso_extract', action='store_true', default=False, help='Skip extracting ISO')
    op.add_option('--skip-livefs-extract', dest='skip_livefs_extract', action='store_true', default=False, help='Skip extracting live filesystem')
    op.add_option('--skip-initrd-extract', dest='skip_initrd_extract', action='store_true', default=False, help='Skip extracting initial ramdisk')
    op.add_option('--skip-iso-create', dest='skip_iso_create', action='store_true', default=False, help='Skip creating ISO')
    op.add_option('--skip-initrd-create', dest='skip_initrd_create', action='store_true', default=False, help='Skip creating Initial Ramdisk')
    #op.add_option('--no-format', dest='no_format', action='store_true', default=False, help='Do not format target device before installation')
    op.add_option('--skip-livefs-create', dest='no_build', action='store_true', default=False, help='Do not build the squash filesystem')
    op.add_option('-o', '--output-file', dest='output_file', help='Specify output file (.iso)')
    op.add_option('--mksquashfs', dest='mksquashfs', help='Specify mksquashfs path')
    op.add_option('--unsquashfs', dest='unsquashfs', help='Specify unsquashfs path')
    op.add_option('--preseed', dest='preseed', help='Add custom preseed to ISO')
    #op.add_option('-c', '--config', action='store_true', dest='config', default=False, help='Configure', metavar='CONFIG')
    opts, args = op.parse_args()
    # check for root privledges
    if os.getuid() == 0:
        # parse options
        if opts.launch_gui:
            import gtk, webbrowser, subprocess
            launch_gui()
            sys.exit(0)
        log.info(settings.APP_COPYRIGHT)
        log.debug('Revision: ' + str(settings.APP_DEV_REV))
        # check dependencies
        depends = check_depends()
        if depends != '':
            log.warning('Please install the following dependencies: %s - Reconstructor will not work properly without them...' % (depends))
        # project file
        if opts.project_file:
            PROJECT = Project(opts.project_file)
            DISTRO_TYPE = PROJECT.distro
            ARCH = PROJECT.arch
            SRC_ISO_FILE = PROJECT.src_iso
            ONLINE = PROJECT.online
            # set online project file
            if ONLINE:
                OUTPUT_FILE = PROJECT.output_file
            # set squashfs-tools
            ver = PROJECT.distro_version.strip()
            if ONLINE:
                if ver == '9.04':
                    MKSQUASHFS = settings.MKSQUASHFS_3_3
                    UNSQUASHFS = settings.UNSQUASHFS_3_3
                elif ver == '9.10':
                    MKSQUASHFS = settings.MKSQUASHFS_4_0
                    UNSQUASHFS = settings.UNSQUASHFS_4_0
                else:
                    log.warn('Unknown distro version.  Using system default squashfs-tools...')
            if '64' in ARCH:
                arch = 'amd64'
            else:
                arch = 'x86'
            if ONLINE:
                #TODO: remove the LVM setup and replace with standard ISO extraction
                log.debug('Online project: creating LVM temporary lvm volume...')
                ptype = PROJECT.project_type.strip().lower()
                base = ''
                env = ''
                if ptype == 'live' or ptype == 'disk':
                    base = 'live'
                    env = PROJECT.environment.strip().lower()
                elif ptype == 'ec2':
                    base = 'ec2'
                    env = 'text'
                else:
                    log.error('Unknown project type.  Cannot create LVM volume.')
                    sys.exit(1)
                lvm_name = '%s_%s_%s_%s_%s' % (PROJECT.distro.strip().lower(), base, env, PROJECT.distro_version.strip().lower(), arch)
                lvm = create_lvm_volume(lvm_name)
                if lvm == False:
                    # report error and exit
                    log_filename = '%s_%s.log' % (PROJECT.name.replace(' ', '_'), PROJECT.author.replace(' ', '_'))
                    # copy log
                    shutil.copy(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'build.log'), os.path.join(settings.ONLINE_ISO_REPO, log_filename))
                    update_job_status(post_url=PROJECT.job_status_post_url, job_id=PROJECT.job_id, action='status', value='error', log_filename=log_filename)
                    sys.exit(1)
                else:
                    WORKING_DIR = lvm

        # check squashfs-tools
        if opts.mksquashfs:
            MKSQUASHFS = opts.mksquashfs
        if opts.unsquashfs:
            UNSQUASHFS = opts.unsquashfs
        # set default squashfs tools
        if MKSQUASHFS == None:
            MKSQUASHFS = commands.getoutput('which mksquashfs')
        if UNSQUASHFS == None:
            UNSQUASHFS = commands.getoutput('which unsquashfs')
        log.debug('SquashFS Tools: %s, %s' % (MKSQUASHFS, UNSQUASHFS))
        # set preseed
        if opts.preseed:
            PRESEED = opts.preseed
        else:
            PRESEED = None
        # check for queue watcher
        if opts.queue:
            start_queue_watcher()
            sys.exit(0)
        # set distro
        if opts.distro_type == None and opts.project_file == None or opts.distro_type == '' and opts.project_file == None:
            op.print_help()
            sys.exit(1)
        elif opts.project_file == None:
            DISTRO_TYPE=opts.distro_type
        
        # set arch
        if opts.arch and opts.project_file == None:
            ARCH=opts.arch
        
        # set description
        if opts.description:
            DESCRIPTION=opts.description

        # set output file
        if opts.output_file:
            OUTPUT_FILE=opts.output_file

        if opts.iso_filename == None and opts.project_file == None and opts.build_only == False and opts.install_only == False and opts.lvm_name == None:
            op.print_help()
            sys.exit(0)
        
        # set custom working dir if necessary
        if opts.working_dir != None and opts.lvm_name == None and opts.project_file == None:
            WORKING_DIR=opts.working_dir
        
        # set LVM
        if opts.lvm_name and not opts.no_build and not opts.project_file:
            WORKING_DIR = create_lvm_volume(lvm_name)

        # check paths
        if os.path.exists(str(opts.iso_filename)):
            SRC_ISO_FILE=opts.iso_filename
        elif opts.build_only == True or opts.install_only == True or opts.project_file or opts.lvm_name:
            pass
        else:
            log.error('Source ISO filename does not exist.')
            sys.exit(1)
        # custom app
        if opts.custom_app != None:
            CUSTOM_APP=opts.custom_app
        # persistent size
        if opts.persistent_size != None:
            PERSISTENT_SIZE=opts.persistent_size
        # add packages
        if opts.add_packages:
            PACKAGES = opts.add_packages.split(',')
        # remove packages
        if opts.remove_packages:
            REMOVE_PACKAGES = opts.remove_packages.split(',')
        # check for distro type
        if opts.build_type.lower() != 'live' and opts.distro_type.lower() != 'ubuntu':
            log.error('Only \'live\' distro types are supported for non-Ubuntu distros...')
            sys.exit(1)
        BUILD_TYPE = opts.build_type.lower() 
        # run
        main()
        sys.exit(0)
    else:
        print('You must be root to run...')
        sys.exit(1)    
    
    



