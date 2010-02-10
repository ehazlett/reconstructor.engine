#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
#    ubuntu.py   
#        Ubuntu distro module
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
import logging
import tempfile
import os
import shutil

class UbuntuDistro(BaseDistro):
    def __init__(self, arch=None, working_dir=None, src_iso_filename=None, online=None, run_post_config=True, mksquashfs=None, unsquashfs=None):
        # call base distro __init__
        super(UbuntuDistro, self).__init__(arch=None, working_dir=working_dir, src_iso_filename=src_iso_filename, online=online, run_post_config=run_post_config)
        self.log = logging.getLogger('UbuntuDistro')
        # set live fs filename
        super(UbuntuDistro, self).set_live_fs_filename(os.path.join(super(UbuntuDistro, self).get_iso_fs_dir(), 'casper' + os.sep + 'filesystem.squashfs'))
        # set local vars
        self.__arch = super(UbuntuDistro, self).get_arch()
        self.__work_dir = super(UbuntuDistro, self).get_work_dir()
        self.__live_fs_dir = super(UbuntuDistro, self).get_live_fs_dir()
        self.__iso_fs_dir = super(UbuntuDistro, self).get_iso_fs_dir()
        self.__initrd_dir = super(UbuntuDistro, self).get_initrd_dir()
        self.__src_iso_filename = super(UbuntuDistro, self).get_src_iso_filename()
        self.__live_fs_filename = super(UbuntuDistro, self).get_live_fs_filename()
        self.__online = super(UbuntuDistro, self).get_online()
        self.__run_post_config = super(UbuntuDistro, self).get_run_post_config()
        self.__mksquash = mksquashfs
        self.__unsquash = unsquashfs

        # check working dirs
        self.check_working_dirs()
    
    def extract_live_fs(self):
        '''Extracts squashfs_filename to self.__squashfs_dir'''
        try:
            # temp mount point for iso
            tmpMntIsoDir = os.path.join(tempfile.gettempdir(), 'r_iso')
            if not fs_tools.mount(self.__src_iso_filename, tmpMntIsoDir):
                self.log.error('Error mounting %s; check log for details...' % (self._src_iso_filename))
                return
            # extract
            squash_tools.extract_squash_fs(unsquashfs_cmd=self.__unsquash, filename=self.__live_fs_filename, dest_dir=self.__live_fs_dir)
            return True
        except Exception, d:
            self.log.error('Error extracting live squash filesystem: %s' % (d))
            return False
        finally:
            # unmount iso
            if not fs_tools.unmount(tmpMntIsoDir):
                self.log.error('Error unmounting %s; check log for details...' % (tmpMntIsoDir))
    
    def update_boot_kernel(self):
        try:
            f = os.listdir('%s' % (os.path.join(self.__live_fs_dir, 'boot')))
            for k in f:
                if k.find('initrd.img') > -1:
                    # copy the initrd to iso dir
                    # check for initrd.gz
                    if os.path.exists(os.path.join(self.__iso_fs_dir, 'casper'+os.sep+'initrd.gz')):
                        self.log.debug('Using %s for initial ramdisk...' % (k))
                        shutil.copy('%s/boot/%s' % (self.__live_fs_dir, k), '%s/casper/initrd.gz' % (self.__iso_fs_dir))
                    # check for initrd.lz
                    if os.path.exists(os.path.join(self.__iso_fs_dir, 'casper'+os.sep+'initrd.lz')):
                        shutil.copy('%s/boot/%s' % (self.__live_fs_dir, k), '%s/casper/initrd.lz' % (self.__iso_fs_dir))
                if k.find('vmlinuz-') > -1:
                    self.log.debug('Using %s for kernel...' % (k))
                    # copy the kernel to iso dir
                    shutil.copy('%s/boot/%s' % (self.__live_fs_dir, k), '%s/casper/vmlinuz' % (self.__iso_fs_dir))

        except Exception, d:
            self.log.error('Error updating boot kernel: %s' % (d))
            return False

    def build_live_fs(self):
        try:
            # update package manifest
            self.log.info('Updating Package manifests...')
            #os.system('chroot %s dpkg -l | awk \'{print $2\" \"$3}\' | tail -n +6 > %s/casper/filesystem.manifest' % (self.__live_fs_dir, self.__iso_fs_dir))
            os.system('chroot %s dpkg-query -W --showformat=\'${Package} ${Version}\n\' > %s/casper/filesystem.manifest' %(self.__live_fs_dir, self.__iso_fs_dir))
            os.system('sed -ie \'/ubiquity/d\' %s/casper/filesystem.manifest' % (self.__iso_fs_dir))
            shutil.copy('%s/casper/filesystem.manifest' % (self.__iso_fs_dir), '%s/casper/filesystem.manifest-desktop' % (self.__iso_fs_dir))
            self.log.info('Building squash filesystem: %s' % (self.__live_fs_filename))
            if squash_tools.create_squash_fs(mksquashfs_cmd=self.__mksquash, source_dir=self.__live_fs_dir, dest_filename=self.__live_fs_filename, overwrite=True):
                if os.path.exists(self.__live_fs_filename):
                    self.log.debug('Live squash filesystem complete: %s' % (self.__live_fs_filename))
                    return True
                else:
                    self.log.error('Error creating squash filesystem; check log for details...')
                    return False
            else:
                self.log.error('Error creating squash filesystem; check log for details...')
                return False
        except Exception, d:
            self.log.error('Error creating squash filesystem: %s : %s' % (self.__live_fs_filename, d))
            return False  
    
    def extract_initrd(self):
        try:
            self.log.debug('Extracting initial ramdisk...')
            if not os.path.exists(self.__initrd_dir):
                os.makedirs(self.__initrd_dir)
            # check for initrd.gz
            if os.path.exists(os.path.join(self.__iso_fs_dir, 'casper'+os.sep+'initrd.gz')):
                initrd = os.path.join(self.__iso_fs_dir, 'casper'+os.sep+'initrd.gz')
                os.system('cd %s; cat %s | gzip -d | cpio -i' % (self.__initrd_dir, initrd))
                return True
            # check for new initrd.lz
            elif os.path.exists(os.path.join(self.__iso_fs_dir, 'casper'+os.sep+'initrd.lz')):
                initrd = os.path.join(self.__iso_fs_dir, 'casper'+os.sep+'initrd.lz')
                os.system('cd %s; unlzma -c -S .lz %s | cpio -id' % (self.__initrd_dir, initrd))
                return True
        except Exception, d:
            self.log.error('Error extracting initrd: %s' % (d))
            return False

    def build_initrd(self):
        try:
            self.log.debug('Building initial ramdisk...')
            # check for initrd.gz
            if os.path.exists(os.path.join(self.__iso_fs_dir, 'casper'+os.sep+'initrd.gz')):
                initrd = os.path.join(self.__iso_fs_dir, 'casper'+os.sep+'initrd.gz')
                os.remove(initrd)
                os.system('cd %s; find | cpio -H newc -o | gzip > %s' % (self.__initrd_dir, initrd))
                return True
            # check for initrd.lz
            elif os.path.exists(os.path.join(self.__iso_fs_dir, 'casper'+os.sep+'initrd.gz')):
                initrd = os.path.join(self.__iso_fs_dir, 'casper'+os.sep+'initrd.lz')
                os.remove(initrd)
                os.system('cd %s; find | cpio -H newc -o | lzma -9 -e > %s' % (self.__initrd_dir, initrd))
                return True
        except Exception, d:
            self.log.error('Error building initrd: %s' % (d))
            return False

    def add_packages(self, packages=None):
        try:
            # add all package repositories
            sources_cfg = os.path.join(os.path.join(os.path.join(self.__live_fs_dir, 'etc'), 'apt'), 'sources.list')
            f = open(sources_cfg, 'r')
            cfg = f.read().split('\n')
            f.close()
            new_cfg = ''
            # enable repos
            for l in cfg:
                if l.find('deb') > -1 and l.find('main') > -1 and l.startswith('#'):
                    new_cfg += l[2:] + '\n'
                elif l.find('deb') > -1 and l.find('restricted') > -1 and l.startswith('#'):
                    new_cfg += l[2:] + '\n'
                elif l.find('deb') > -1 and l.find('universe') > -1 and l.startswith('#'):
                    new_cfg += l[2:] + '\n'
                elif l.find('deb') > -1 and l.find('multiverse') > -1 and l.startswith('#'):
                    new_cfg += l[2:] + '\n'
                else:
                    new_cfg += l + '\n'
            f = open(sources_cfg, 'w')
            f.write(new_cfg)
            f.close()

            # create 'apt-get install' package list
            pkg_list = ''
            dpkg_pkgs = ''
            java_version = None
            if len(packages) > 0:
                if type(packages) is type({}):
                    for p in packages:
                        #pkg_list += '%s=%s ' % (p, packages[p])
                        pkg_list += '%s ' % (p)
                        dpkg_pkgs += '%s ' % (p)
                else:
                    for p in packages:
                        pkg_list += '%s ' % (p)
                # check for java
                for p in packages:
                    if p.find('java') > 0:
                        java_version = p[p.find('java')+4]
                # create java license bypass script
                jv = java_version
                # HACK: set the bypass for java 5,6 - will halt package installation if a package relies on java...
                # for java 5
                java_bypass = 'sun-java5-bin shared/accepted-sun-dlj-v1-1 boolean true\nsun-java5-jdk  shared/accepted-sun-dlj-v1-1 boolean true\nsun-java5-jre shared/accepted-sun-dlj-v1-1 boolean true\nsun-java5-jre sun-java5-jre/stopthread boolean true\nsun-java5-jre sun-java5-jre/jcepolicy note\nsun-java5-bin shared/present-sun-dlj-v1-1 note\nsun-java5-jdk shared/present-sun-dlj-v1-1 note\nsun-java5-jre shared/present-sun-dlj-v1-1 note\n'
                # for java 6
                java_bypass += 'sun-java6-bin shared/accepted-sun-dlj-v1-1 boolean true\nsun-java6-jdk  shared/accepted-sun-dlj-v1-1 boolean true\nsun-java6-jre shared/accepted-sun-dlj-v1-1 boolean true\nsun-java6-jre sun-java6-jre/stopthread boolean true\nsun-java6-jre sun-java6-jre/jcepolicy note\nsun-java6-bin shared/present-sun-dlj-v1-1 note\nsun-java6-jdk shared/present-sun-dlj-v1-1 note\nsun-java5-jre shared/present-sun-dlj-v1-1 note\n'
                # create temp script
                scr_file = os.path.join(os.path.join(self.__live_fs_dir, 'tmp'), 'pkgs.sh')
                f = open(scr_file, 'w')
                if self.__online:
                    if settings.APT_CACHER_ADDRESS != '':
                        f.write('#!/bin/sh\n# Reconstructor package install script\nexport http_proxy=http://%s\necho \'%s\' | debconf-set-selections\napt-get update\nDEBIAN_FRONTEND=noninteractive apt-get install -f -y --force-yes %s\n\napt-get clean\napt-get autoclean\n\n' % (settings.APT_CACHER_ADDRESS, java_bypass, pkg_list))
                    else:
                        f.write('#!/bin/sh\n# Reconstructor package install script\necho \'%s\' | debconf-set-selections\napt-get update\nDEBIAN_FRONTEND=noninteractive apt-get install -f -y --force-yes %s\n\napt-get clean\napt-get autoclean\n\n' % (java_bypass, pkg_list))
                else:
                    f.write('#!/bin/sh\n# Reconstructor package install script\necho \'%s\' | debconf-set-selections\napt-get update\nDEBIAN_FRONTEND=noninteractive apt-get install -f -y --force-yes %s\n\napt-get clean\napt-get autoclean\n\n' % (java_bypass, pkg_list))
                f.close()
                # make script executable
                os.chmod(scr_file, 0775)
                self.log.debug('Package list: %s' % (pkg_list))
                # install
                os.system('chroot %s /tmp/pkgs.sh' % (self.__live_fs_dir))
                # cleanup
                os.remove(os.path.join(os.path.join(self.__live_fs_dir, 'tmp'), 'pkgs.sh'))
                # post config
                if self.__run_post_config and type(p) is type({}):
                    # check for X -- if so use xterm for config
                    post_cfg = os.path.join(self.__live_fs_dir, 'usr' + os.sep + 'bin' + os.sep + 'r_post_cfg.sh')
                    if os.path.exists(os.path.join(self.__live_fs_dir, 'usr' + os.sep + 'bin' + os.sep + 'X')):
                        self.log.debug('Using xterm for Post Config...')
                        f = open(post_cfg, 'w')
                        f.write('# Reconstructor Post Configuration Script\n#\n\nUSER=`who | head -n 1 | awk \'{print $1}\'`\nXRUN=`ps aux | grep X | wc -l`\nif [ ! -f /usr/share/reconstructor/postcfg_run ]; then  echo \"\nStarting Reconstructor Post Configuration...\"; sleep 5; if [ `runlevel | awk \'{print $2}\'` = \"2\" ]; then  sleep 5; sudo -u $USER xterm -display :0 -title \"Reconstructor Package Configuration\" -e \"sudo dpkg-reconfigure %s\"; mkdir -p /usr/share/reconstructor; touch /usr/share/reconstructor/postcfg_run; fi; fi\n\n' % (dpkg_pkgs))
                        f.close()
                    else:
                        self.log.debug('Using terminal for Post Config...')
                        f = open(post_cfg, 'w')
                        f.write('\n\n# Reconstructor Post Configuration\n\nif [ ! -f /usr/share/reconstructor/postcfg_run ]; then  echo \"Starting Reconstructor Post Configuration\" ; sleep 1 ; dpkg-reconfigure %s; mkdir -p /usr/share/reconstructor; touch /usr/share/reconstructor/postcfg_run; fi\n' % (dpkg_pkgs))
                        f.close()
                
                    # make executable
                    os.chmod(post_cfg, 0775)

                    # add post config to rc.local
                    cfg = ''
                    f = open(os.path.join(self.__live_fs_dir, 'etc' + os.sep + 'rc.local'), 'r')
                    o = f.read()
                    f.close()
                    for l in o.split('\n'):
                        if l.find('exit') > -1:
                            cfg += '/usr/bin/r_post_cfg.sh \nexit 0\n'
                            break
                        else:
                            cfg += l + '\n'
                    f = open(os.path.join(self.__live_fs_dir, 'etc' + os.sep + 'rc.local'), 'w')
                    f.write(cfg)
                    f.close()
                
                # kill all running process to prevent unmount errors
                self.log.debug('Stopping all running process in chroot...')
                if self.__online:
                    os.system('fuser -km %s' % (self.__live_fs_dir))
                # TODO:  kill processes running in standalone engine -- if use above, crashes gnome-session...
        except Exception, d:
            self.log.error('Error adding packages: %s' % (d))
            return False
        
        
    def enable_persistent_fs(self, size=64):
        '''Enables the casper-rw filesystem for saving changes between live sessions'''
        try:
            self.log.debug('Creating persistent filesystem...')
            # create the external filesystem
            os.system('dd if=/dev/zero of=%s/casper-rw bs=1M count=%s > %s' % (self.__iso_fs_dir, str(size), os.devnull))
            # format
            self.log.debug('Formatting persistent filesystem...')
            os.system('mkfs.ext3 -F %s/casper-rw > %s' % (self.__iso_fs_dir, os.devnull))
            self.log.debug('Creating automount for persistent filesystem...')
            #f = open('%s/etc/rc.local' % (self.__squashfs_dir) ,'w')
            #f.write('# custom rc.local for reconstructor custom\n\n# automount persistent filesystem\nmkdir /mnt/extfs\nmount -o loop /cdrom/persist.fs /mnt/extfs\nchmod -R a+rw /mnt/extfs\n\nexit 0\n')
            #f.close()
        except Exception, d:
            self.log.error('Error creating persistant filesystem: %s' % (d))
            return False
    
    
    
    
    
    

