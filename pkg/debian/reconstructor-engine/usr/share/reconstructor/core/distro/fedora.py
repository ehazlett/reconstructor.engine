#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
#    fedora.py   
#        Fedora distro module
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


from reconstructor.core.distro.base import BaseDistro
from reconstructor.core import fs_tools
from reconstructor.core import squash_tools
from reconstructor import settings
import logging
import tempfile
import os
import shutil
import commands

class FedoraDistro(BaseDistro):
    def __init__(self, arch=None, working_dir=None, src_iso_filename=None, online=None, run_post_config=True, mksquashfs=None, unsquashfs=None):
        # call base distro __init__
        super(FedoraDistro, self).__init__(arch=None, working_dir=working_dir, src_iso_filename=src_iso_filename, online=online, run_post_config=run_post_config)
        self.log = logging.getLogger('FedoraDistro')
        # set live fs filename
        super(FedoraDistro, self).set_live_fs_filename(os.path.join(super(FedoraDistro, self).get_iso_fs_dir(), 'LiveOS' + os.sep + 'squashfs.img'))
        # set local vars
        self.__arch = super(FedoraDistro, self).get_arch()
        self.__work_dir = super(FedoraDistro, self).get_work_dir()
        self.__live_fs_dir = super(FedoraDistro, self).get_live_fs_dir()
        self.__iso_fs_dir = super(FedoraDistro, self).get_iso_fs_dir()
        self.__initrd_dir = super(FedoraDistro, self).get_initrd_dir()
        self.__src_iso_filename = super(FedoraDistro, self).get_src_iso_filename()
        self.__live_fs_filename = super(FedoraDistro, self).get_live_fs_filename()
        self.__online = super(FedoraDistro, self).get_online()
        self.__run_post_config = super(FedoraDistro, self).get_run_post_config()
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
            # fedora uses an ext image -- extract that first, then copy the contents
            tmpdir = tempfile.mkdtemp()
            tmpImgDir = tempfile.mkdtemp()
            self.log.debug('Extracting squash filesystem: %s' % (self.__live_fs_filename))
            squash_tools.extract_squash_fs(unsquashfs_cmd=self.__unsquash, filename=self.__live_fs_filename, dest_dir=tmpdir)
            # mount the ext image
            self.log.debug('Mounting filesystem...')
            fs_tools.mount(os.path.join(tmpdir, 'LiveOS' + os.sep + 'ext3fs.img'), tmpImgDir)
            commands.getoutput('rsync -a %s/ %s/' % (tmpImgDir, self.__live_fs_dir))
            return True
        except Exception, d:
            self.log.error('Error extracting live squash filesystem: %s' % (d))
            return False
        finally:
            # unmount iso
            if not fs_tools.unmount(tmpMntIsoDir):
                self.log.error('Error unmounting %s; check log for details...' % (tmpMntIsoDir))
            if not fs_tools.unmount(tmpImgDir):
                self.log.error('Error unmounting %s; check log for details...' % (tmpImgDir))
            #shutil.rmtree(tmpdir)

    def update_boot_kernel(self):
        try:
            f = os.listdir('%s' % (os.path.join(self.__live_fs_dir, 'boot')))
            for k in f:
                if k.find('initrd.img') > -1:
                    # copy the initrd to iso dir
                    shutil.copy('%s/boot/%s' % (self.__live_fs_dir, k), '%s/isolinux/initrd0.img' % (self.__iso_fs_dir))
                if k.find('vmlinuz-') > -1:
                    # copy the kernel to iso dir
                    shutil.copy('%s/boot/%s' % (self.__live_fs_dir, k), '%s/isolinux/vmlinuz0' % (self.__iso_fs_dir))

        except Exception, d:
            self.log.error('Error updating boot kernel: %s' % (d))
            return False

    def build_live_fs(self):
        try:
            self.log.debug('Creating sparse image...')
            tmpImgDir = tempfile.mkdtemp()
            tmpSquashDir = tmpImgDir + os.sep + 'LiveOS'
            tmpMntDir = tempfile.mkdtemp()
            os.makedirs(tmpSquashDir)
            os.system('dd if=/dev/zero of=%s/ext3fs.img bs=1M count=0 seek=4096' % (tmpSquashDir))
            os.system('mkfs.ext3 -F %s' % (os.path.join(tmpSquashDir, 'ext3fs.img')))
            # mount
            fs_tools.mount(os.path.join(tmpSquashDir, 'ext3fs.img'), tmpMntDir)
            # copy files
            os.system('rsync -a %s/ %s/' % (self.__live_fs_dir, tmpMntDir))
            self.log.info('Building squash filesystem: %s' % (self.__live_fs_filename))
            if squash_tools.create_squash_fs(mksquashfs_cmd=self.__mksquash, source_dir=tmpImgDir, dest_filename=self.__live_fs_filename, overwrite=True):
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
        finally:
            fs_tools.unmount(tmpMntDir)
            # cleanup
            shutil.rmtree(tmpImgDir)
    
    def extract_initrd(self):
        self.log.error('Not implemented...')
        return
        try:
            self.log.debug('Extracting initial ramdisk...')
            if not os.path.exists(self.__initrd_dir):
                os.makedirs(self.__initrd_dir)
            initrd = os.path.join(self.__iso_fs_dir, 'casper'+os.sep+'initrd.gz')
            os.system('cd %s; cat %s | gzip -d | cpio -i' % (self.__initrd_dir, initrd))
            return True
        except Exception, d:
            self.log.error('Error extracting initrd: %s' % (d))
            return False

    def build_initrd(self):
        self.log.error('Not implemented...')
        return
        try:
            self.log.debug('Building initial ramdisk...')
            initrd = os.path.join(self.__iso_fs_dir, 'casper'+os.sep+'initrd.gz')
            os.remove(initrd)
            os.system('cd %s; find | cpio -H newc -o | gzip > %s' % (self.__initrd_dir, initrd))
            return True
        except Exception, d:
            self.log.error('Error building initrd: %s' % (d))
            return False

    def add_packages(self, packages=None):
        self.log.error('Not implemented...')
        return
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
            if len(packages) > 0:
                if type(packages) is type({}):
                    for p in packages:
                        #pkg_list += '%s=%s ' % (p, packages[p])
                        pkg_list += '%s ' % (p)
                        dpkg_pkgs += '%s ' % (p)
                else:
                    for p in packages:
                        pkg_list += '%s ' % (p)
                # create temp script
                scr_file = os.path.join(os.path.join(self.__live_fs_dir, 'tmp'), 'pkgs.sh')
                f = open(scr_file, 'w')
                if self.__online:
                    if settings.APT_CACHER_ADDRESS != '':
                        f.write('#!/bin/sh\n# Reconstructor package install script\nexport http_proxy=http://%s\napt-get update\nDEBIAN_FRONTEND=noninteractive apt-get install -f -y --force-yes %s\n\napt-get clean\napt-get autoclean\n\n' % (settings.APT_CACHER_ADDRESS, pkg_list))
                    else:
                        f.write('#!/bin/sh\n# Reconstructor package install script\n\napt-get update\nDEBIAN_FRONTEND=noninteractive apt-get install -f -y --force-yes %s\n\napt-get clean\napt-get autoclean\n\n' % (pkg_list))
                else:
                    f.write('#!/bin/sh\n# Reconstructor package install script\n\napt-get update\nDEBIAN_FRONTEND=noninteractive apt-get install -f -y --force-yes %s\n\napt-get clean\napt-get autoclean\n\n' % (pkg_list))
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
        self.log.error('Not implemented...')
        return
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
    
    
    
    
    
    

