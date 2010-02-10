#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
#    ubuntu_ec2.py
#        Ubuntu EC2 distro module
#    Copyright (c) <2009> Reconstructor Team <reconstructor@aperantis.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from reconstructor.core.distro.base import BaseDistro
from reconstructor.core import fs_tools
from reconstructor.core import squash_tools
from reconstructor import settings
import commands
import logging
import tempfile
import os

class UbuntuEC2Distro(BaseDistro):
    def __init__(self, arch=None, working_dir=None):
        # call base distro __init__
        super(UbuntuEC2Distro, self).__init__(arch=None, working_dir=working_dir)
        self.log = logging.getLogger('UbuntuEC2Distro')
        # set local vars
        self.__arch = arch 
        self.__work_dir = super(UbuntuEC2Distro, self).get_work_dir()
        super(UbuntuEC2Distro, self).set_live_fs_dir(os.path.join(self.__work_dir, 'root_fs'))
        self.__live_fs_dir = super(UbuntuEC2Distro, self).get_live_fs_dir()

        # check working dirs
        self.check_working_dirs()
    
    def build_ec2_ami(self, prefix=None, cert=None, key=None, id=None):
        try:
            self.log.info('Building EC2 bundle...')
            # check for existing image
            if os.path.exists(os.path.join(tempfile.gettempdir(), prefix)):
                self.log.info('Removing existing EC2 image...')
                os.system('rm -rf %s/%s*' % (tempfile.gettempdir(), prefix))
            arch = ''
            if self.__arch == 'x86':
                arch = 'i386'
            elif self.__arch == 'amd64':
                arch = 'x86_64'
            self.log.debug('Arch: %s' % (arch))
            self.log.debug('Bundling EC2 image: %s' % (prefix))
            self.log.info(commands.getoutput('ec2-bundle-vol -c %s -k %s -u %s --batch --no-inherit -r %s -v %s -p %s' % (cert, key, id, arch, self.__live_fs_dir, prefix)))
            return True
        except Exception, d:
            self.log.error('Error bundling EC2 image: %s' % (d))
            return False
    
    def upload_ec2_ami(self, prefix=None, s3_id=None, s3_key=None, s3_bucket=None):
        try:
            self.log.info('Uploading %s to S3 bucket %s...' % (prefix, s3_bucket))
            self.log.info(commands.getoutput('ec2-upload-bundle -b %s -m %s/%s.manifest.xml -a %s -s %s --batch' % (s3_bucket, tempfile.gettempdir(), prefix, s3_id, s3_key)))
            return True
        except Exception, d:
            self.log.error('Error uploading to S3: %s' % (d))
            return False
        finally:
            if settings.LOG_LEVEL != logging.DEBUG:
                self.log.info('Cleaning up...')
                if os.path.exists(os.path.join(tempfile.gettempdir(), prefix)):
                    self.log.info('Removing built EC2 image...')
                    os.system('rm -rf %s/%s*' % (tempfile.gettempdir(), prefix))
        

    def add_public_ssh_credentials(self):
        try:
            self.log.debug('Adding Public SSH Credentials...')
            f = open(os.path.join(self.__live_fs_dir, 'etc' + os.sep + 'rc.local'), 'w')
            f.write('\n\nif [ ! -d /root/.ssh ] ; then\n\tmkdir -p /root/.ssh\n\tchmod 700 /root/.ssh\nfi\n\ncurl http://169.254.169.254/2009-04-04//meta-data/public-keys/0/openssh-key > /tmp/my-key\nif [ $? -qa 0 ] ; then\n\tcat /tmp/my-key >> /root/.ssh/authorized_keys\n\tchmod 700 /root/.ssh/authorized_keys\n\trm /tmp/my-key\nfi\n\nexit 0')
            f.close()
        except Exception, d:
            self.log.error(d)

    def add_packages(self, packages=None):
        try:
            # add all package repositories
            sources_cfg = os.path.join(os.path.join(os.path.join(self.__live_fs_dir, 'etc'), 'apt'), 'sources.list')
            f = open(sources_cfg, 'r')
            cfg = f.read()
            f.close()
            new_cfg = ''
            # enable repos
            r = ['main', 'universe', 'restricted', 'multiverse']
            for x in r:
                t = cfg
                new_cfg += t.replace('main', x) + '\n'
            f = open(sources_cfg, 'w')
            f.write(new_cfg)
            f.close()

            # create 'apt-get install' package list
            pkg_list = ''
            dpkg_pkgs = ''
            if len(packages) > 0:
                for p in packages:
                    pkg_list += '%s=%s ' % (p, packages[p])
                    dpkg_pkgs += '%s ' % (p)
                # create temp script
                scr_file = os.path.join(os.path.join(self.__live_fs_dir, 'tmp'), 'pkgs.sh')
                f = open(scr_file, 'w')
                if settings.APT_CACHER_ADDRESS != '':
                    f.write('#!/bin/sh\n# Reconstructor package install script\nexport http_proxy=http://%s\napt-get update\nDEBIAN_FRONTEND=noninteractive apt-get install -f -y --force-yes %s\n\napt-get clean\napt-get autoclean\n\n' % (settings.APT_CACHER_ADDRESS, pkg_list))
                else:
                    f.write('#!/bin/sh\n# Reconstructor package install script\n\napt-get update\nDEBIAN_FRONTEND=noninteractive apt-get install -f -y --force-yes %s\n\napt-get clean\napt-get autoclean\n\n' % (pkg_list))
                f.close()
                # make scripts executable
                os.chmod(scr_file, 0775)
                self.log.debug('Package list: %s' % (pkg_list))
                # install
                os.system('chroot %s /tmp/pkgs.sh' % (self.__live_fs_dir))
                # cleanup
                os.remove(os.path.join(os.path.join(self.__live_fs_dir, 'tmp'), 'pkgs.sh'))
                # kill all running process to prevent unmount errors
                self.log.debug('Stopping all running process in chroot...')
                os.system('fuser -km %s' % (self.__live_fs_dir))
        except Exception, d:
            self.log.error('Error adding packages: %s' % (d))
            return False
        
        

