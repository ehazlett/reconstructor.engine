#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
#    ubuntu.py   
#        Ubuntu distro module
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
import subprocess
import urllib
import bz2
import gzip
import commands
import getpass
import tarfile

class UbuntuDistro(BaseDistro):
    def __init__(self, arch=None, working_dir=None, src_iso_filename=None, online=None, run_post_config=True, mksquashfs=None, unsquashfs=None, build_type=None):
        # call base distro __init__
        super(UbuntuDistro, self).__init__(arch=None, working_dir=working_dir, src_iso_filename=src_iso_filename, online=online, run_post_config=run_post_config, build_type=build_type)
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
        self.__build_type = super(UbuntuDistro, self).get_build_type()
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
            elif os.path.exists(os.path.join(self.__iso_fs_dir, 'casper'+os.sep+'initrd.lz')):
                initrd = os.path.join(self.__iso_fs_dir, 'casper'+os.sep+'initrd.lz')
                os.remove(initrd)
                os.system('cd %s; find . | cpio --quiet --dereference -o -H newc | lzma -7 > %s' % (self.__initrd_dir, initrd))
                return True
        except Exception, d:
            self.log.error('Error building initrd: %s' % (d))
            return False

    def get_gpg_email(self):
        email = ''
        while email == '':
            email = raw_input('Enter GPG key email address: ').strip()
        return email

    def get_gpg_passphrase(self):
        pswd = ''
        while pswd == '':
            pswd = getpass.getpass('Enter GPG passphrase: ').strip()
        return pswd
    
    def get_dependencies(self, package=None, packages_file=None):
        pkgs = []
        pkg_found = False
        f = open(packages_file, 'r')
        for l in f.read().split('\n'):
            if l.find('Package: %s' % (package)) > -1:
                pkg_found = True
            if pkg_found and l.find('Depends') > -1:
                s = l.split('Depends:')[1]
                for p in s.split(','):
                    pname = p.split()[0]
                    if pname not in pkgs:
                        pkgs.append(pname)
            if pkg_found and l.find('Description') > -1:
                break
        return pkgs

    def add_packages(self, packages=None):
        try:
            if self.__build_type == 'live':
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
                    java_bypass += 'sun-java6-bin shared/accepted-sun-dlj-v1-1 boolean true\nsun-java6-doc shared/accepted-sun-dlj-v1-1 boolean true\nsun-java6-jdk  shared/accepted-sun-dlj-v1-1 boolean true\nsun-java6-jre shared/accepted-sun-dlj-v1-1 boolean true\nsun-java6-jre sun-java6-jre/stopthread boolean true\nsun-java6-jre sun-java6-jre/jcepolicy note\nsun-java6-bin shared/present-sun-dlj-v1-1 note\nsun-java6-jdk shared/present-sun-dlj-v1-1 note\nsun-java5-jre shared/present-sun-dlj-v1-1 note\n'
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
            elif self.__build_type == 'alternate':
                tmp_dir = tempfile.mkdtemp()
                # find 'release' version
                if not os.path.exists(os.path.join(self.__iso_fs_dir, '.disk' + os.sep + 'info')):
                    self.log.error('Unable to find release version for distro...')
                    return False
                f = open(os.path.join(self.__iso_fs_dir, '.disk' + os.sep + 'info'), 'r')
                ver = f.read()
                f.close()
                # find ubuntu codename
                # look for 'LTS' for the long term support releases
                if ver.split()[2].lower() != 'lts':
                    distro_codename = ver.split()[2].replace('"', '').lower()
                    distro_version = ver.split()[1]
                    distro_arch = ver.split()[6]
                else:
                    distro_codename = ver.split()[3].replace('"', '').lower()
                    distro_version = ver.split()[1]
                    distro_arch = ver.split()[7]
                if len(packages) > 0:
                    pkg_list = ''
                    if type(packages) is type({}):
                        for p in packages:
                            #pkg_list += '%s=%s ' % (p, packages[p])
                            pkg_list += '%s ' % (p)
                            dpkg_pkgs += '%s ' % (p)
                    else:
                        for p in packages:
                            pkg_list += '%s ' % (p)
                    # generate preseed; append to existing ubuntu.seed if exists
                    self.log.debug('Generating preseed...')
                    ubuntu_seed_file = os.path.join(self.__iso_fs_dir, 'preseed' + os.sep + 'ubuntu.seed')
                    ubuntu_seed = None
                    if os.path.exists(ubuntu_seed_file):
                        self.log.debug('Using Ubuntu preseed...')
                        f = open(ubuntu_seed_file, 'r')
                        ubuntu_seed = f.read()
                        f.close()
                    preseed_file = os.path.join(tmp_dir, 'custom.seed')
                    f = open(preseed_file, 'w')
                    if ubuntu_seed:
                        f.write(ubuntu_seed+'\n')
                    f.write('d-i pkgsel/include %s\n\n' % (pkg_list))
                    f.close()
                    # copy to preseed dir
                    shutil.copy(preseed_file, os.path.join(self.__iso_fs_dir, 'preseed' + os.sep + 'custom.seed'))
                    # update isolinux
                    self.log.debug('Updating isolinux configuration...')
                    isolinux_cfg_file = os.path.join(self.__iso_fs_dir, 'isolinux' + os.sep + 'text.cfg')
                    isolinux_cfg = ''
                    f = open(isolinux_cfg_file, 'r')
                    for l in f.read().split('\n'):
                        if l.find('ubuntu.seed') > -1:
                            isolinux_cfg += '%s\n' % (l.replace('ubuntu.seed', 'custom.seed'))
                        else:
                            isolinux_cfg += '%s\n' % (l)
                    f.close()
                    f = open(isolinux_cfg_file, 'w')
                    f.write(isolinux_cfg)
                    f.close()

                # build release file for extras - even if no packages were specified on command line
                if len(packages) > 0 or os.path.exists(os.path.join(self.__iso_fs_dir, 'pool' + os.sep + 'extras')):
                    # add packages to alt disc
                    self.log.info('Getting package lists for %s...' % (distro_codename))
                    # download package lists for each repo
                    repo_url = 'http://archive.ubuntu.com/ubuntu/dists/%s' % (distro_codename)
                    pkgs_file = os.path.join(tmp_dir, 'packages')
                    for x in ['main','restricted','universe','multiverse']:
                        self.log.debug('Getting %s package list...' % (x))
                        pkg_bz2 = os.path.join(tmp_dir, '%s_packages.bz2' % (x))
                        pkg_file = os.path.join(tmp_dir, '%s_packages' % (x))
                        urllib.urlretrieve('%s/%s/binary-%s/Packages.bz2' % (repo_url, x, distro_arch), filename=pkg_bz2)
                        # extract
                        self.log.debug('Extracting...')
                        b = bz2.BZ2File(pkg_bz2)
                        f = open(pkg_file, 'w')
                        f.write(b.read())
                        f.close()
                        b.close()
                        # append pkg_file to pkgs_file
                        f1 = open(pkg_file, 'r')
                        f2 = open(pkgs_file, 'a')
                        f2.write(f1.read())
                        f1.close()
                        f2.close()
                        # cleanup
                        os.remove(pkg_bz2)
                        os.remove(pkg_file)

                    # find and download each package specified as well as ubuntu-keyring source
                    packages.append('ubuntu-keyring')
                    # load base package list from local repository
                    self.log.debug('Loading local repository packages...')
                    base_packages = []
                    # load local repo Packages
                    local_pkgs_file = os.path.join(tmp_dir, 'local_packages')
                    for p in os.listdir(os.path.join(self.__iso_fs_dir, 'dists')):
                        self.log.debug('Loading packages for local repo dist: %s' % (p))
                        # load repos
                        for d in os.listdir(os.path.join(self.__iso_fs_dir, 'dists' + os.sep + p)):
                            pkg_file = os.path.join(self.__iso_fs_dir, 'dists' + os.sep + p + os.sep + d + os.sep + 'binary-' + distro_arch + os.sep + 'Packages.gz')
                            if os.path.exists(pkg_file):
                                self.log.debug('Loading %s' % (d))
                                g = gzip.open(pkg_file)
                                f = open(local_pkgs_file, 'a')
                                f.write(g.read())
                                f.close()
                                g.close()
                    # load base packages from local packages file
                    f = open(local_pkgs_file, 'r')
                    for l in f.read().split('\n'):
                        if l.find('Package:') > -1:
                            pkg = l.split('Package:')[1].strip()
                            base_packages.append(pkg)
                    f.close()
                    # load package dependencies
                    pkg_count = len(packages)
                    self.log.info('Resolving dependencies...')
                    while True:
                        # get dependencies of packages
                        for p in packages:
                            depends = self.get_dependencies(p, pkgs_file)
                            #self.log.debug('Dependencies for %s: %s' % (p, depends))
                            [packages.append(x) for x in depends if x not in packages and x not in base_packages]
                        pkg_count = len(packages)
                        if len(packages) == pkg_count:
                            break
                    self.log.debug('All packages needed: %s' % (packages))
                    self.log.info('Download packages...')
                    for p in packages:
                        self.log.debug('Searching for package %s...' % (p))
                        pkg_found = False
                        f = open(pkgs_file, 'r')
                        for l in f.read().split('\n'):
                            if l.find('Package: %s' % (p)) > -1:
                                pkg_found = True
                            if pkg_found and l.find('Filename') > -1:
                                # download package to local repo
                                pkg_url = l.split()[1]
                                self.log.debug('Downloading %s...' % (p))
                                if p == 'ubuntu-keyring':
                                    self.log.debug('Getting ubuntu-keyring source...')
                                    if pkg_url.find('_all') > -1:
                                        pkg_url = pkg_url.replace('_all.deb', '.tar.gz')
                                    else:
                                        pkg_url = pkg_url.replace('.deb', '.tar.gz')
                                    urllib.urlretrieve('http://archive.ubuntu.com/ubuntu/%s' % pkg_url, filename=os.path.join(tmp_dir, pkg_url.split('/')[-1]))
                                    # extract ubuntu-keyring source
                                    self.log.debug('Extracting ubuntu-keyring source...')
                                    t = tarfile.open(os.path.join(tmp_dir, pkg_url.split('/')[-1]))
                                    t.extractall(path=tmp_dir)
                                    t.close()
                                else:
                                    urllib.urlretrieve('http://archive.ubuntu.com/ubuntu/%s' % pkg_url, filename=os.path.join(tmp_dir, pkg_url.split('/')[-1]))
                            if pkg_found and l.find('Description') > -1:
                                break
                        if not pkg_found:
                            self.log.warn('Unable to find package: %s' % (p))
                    # create 'extras' component
                    self.log.debug('Creating Extras component...')
                    extra_dist = os.path.join(self.__iso_fs_dir, 'dists' + os.sep + distro_codename + os.sep + 'extras' + os.sep + 'binary-' + distro_arch)
                    extra_pool = os.path.join(self.__iso_fs_dir, 'pool' + os.sep + 'extras')
                    if not os.path.exists(extra_dist):
                        os.makedirs(extra_dist)
                    if not os.path.exists(extra_pool):
                        os.makedirs(extra_pool)
                    # copy files
                    for x in os.listdir(tmp_dir):
                        if x.find('.deb') > -1:
                            self.log.debug('Copying %s to extra pool...' % (x))
                            shutil.copy(os.path.join(tmp_dir, x), os.path.join(extra_pool, x))
                    # create release file for extras
                    self.log.debug('Generating Release file...')
                    f = open(os.path.join(self.__iso_fs_dir, 'dists' + os.sep + distro_codename + os.sep + 'extras' + os.sep + 'binary-' + distro_arch + os.sep + 'Release'), 'w')
                    f.write('Archive: %s\nVersion: %s\nComponent: extras\nOrigin: Ubuntu\nLabel: Ubuntu\nArchitecture: %s\n' % (distro_codename, distro_version, distro_arch))
                    f.close()
                    # generate GPG key
                    key_name = 'Alternate Installation Automatic Signing Key'
                    key_comment = 'Reconstructor Signing Key'
                    output = commands.getoutput('gpg --list-keys | grep \'%s\'' % (key_name))
                    if output != '':
                        self.log.debug('GPG key found...')
                    else:
                        self.log.debug('No GPG key found; creating...')
                        key_email = self.get_gpg_email()
                        key_passphrase = self.get_gpg_passphrase()
                        key = 'Key-Type: DSA\nKey-Length: 1024\nSubkey-Type: ELG-E\nSubkey-Length: 2048\nName-Real: %s\nName-Comment: %s\nName-Email: %s\nExpire-Date: 0\nPassphrase: %s' % (key_name, key_comment, key_email, key_passphrase)
                        f = open(os.path.join(tmp_dir, 'gpg.key'), 'w')
                        f.write(key)
                        f.close()
                        # create key
                        self.log.debug('Generating GPG key...')
                        p = subprocess.Popen('gpg --gen-key --batch %s > /dev/null' % (os.path.join(tmp_dir, 'gpg.key')), shell=True)
                        os.waitpid(p.pid, 0)
                        # reset permissions for user
                        p = subprocess.Popen('chown -R %s %s/.gnupg/' % (os.getlogin(), os.environ['HOME']), shell=True)
                        os.waitpid(p.pid, 0)

                    # import gpg key
                    for d in os.listdir(tmp_dir):
                        if d.find('ubuntu-keyring') > -1 and d.find('.gz') == -1:
                            self.log.debug('Importing Ubuntu key...')
                            ubuntu_keyring_file = os.path.join(tmp_dir, d + os.sep + 'keyrings' + os.sep + 'ubuntu-archive-keyring.gpg')
                            p = subprocess.Popen('gpg --import %s' % (ubuntu_keyring_file), shell=True)
                            os.waitpid(p.pid, 0)
                            # export custom gpg key
                            self.log.debug('Exporting custom GPG key...')
                            # remove existing
                            os.remove(ubuntu_keyring_file)
                            p = subprocess.Popen('gpg --output=%s --export \"%s\" 2>&1 > /dev/null' % (ubuntu_keyring_file, key_name), shell=True)
                            os.waitpid(p.pid, 0)
                            # build new ubuntu-keyring package
                            self.log.debug('Building keyring package...')
                            p = subprocess.Popen('cd %s ; dpkg-buildpackage -rfakeroot -m\"Reconstructor <info@reconstructor.org>\" -k\"%s\" > /dev/null' % (os.path.join(tmp_dir, d), key_name), shell=True)
                            os.waitpid(p.pid, 0)
                            # copy package to pool
                            main_pool_dir = os.path.join(self.__iso_fs_dir, 'pool' + os.sep + 'main' + os.sep + 'u' + os.sep + 'ubuntu-keyring')
                            for p in os.listdir(main_pool_dir):
                                self.log.debug('Removing existing ubuntu-keyring package: %s' % (p))
                                os.remove(os.path.join(main_pool_dir, p))
                            for p in os.listdir(tmp_dir):
                                if p.find('ubuntu-keyring') > -1:
                                    if p.find('deb') > -1:
                                        # copy to main pool
                                        self.log.debug('Copying %s to main pool...' % (p))
                                        shutil.copy(os.path.join(tmp_dir, p), os.path.join(main_pool_dir, p))
                            break
                    # build the repo
                    index_dir = os.path.join(tmp_dir, 'indices')
                    ftparchive_dir = os.path.join(tmp_dir, 'apt-ftparchive')
                    os.makedirs(index_dir)
                    os.makedirs(ftparchive_dir)
                    for d in ['extra.main','main','main.debian-installer','restricted','restricted.debian-installer']:
                        self.log.debug('Getting override: %s...' % (d))
                        urllib.urlretrieve('http://archive.ubuntu.com/ubuntu/indices/override.%s.%s' % (distro_codename, d), filename=os.path.join(index_dir, 'override.%s.%s' % (distro_codename, d)))
                    self.log.debug('Generating apt-ftparchive config files...')
                    # create apt-ftparchive-deb.conf
                    f = open(os.path.join(ftparchive_dir, 'apt-ftparchive-deb.conf'), 'w')
                    f.write('Dir {\n\tArchiveDir \"%s/\";\n};\n\nTreeDefault {\n\tDirectory \"pool/\";\n};\n\nBinDirectory \"pool/main\" {\n\tPackages \"dists/%s/main/binary-%s/Packages\";\n\tBinOverride \"%s/override.%s.main\";\n\tExtraOverride \"%s/override.%s.extra.main\";\n};\n\nBinDirectory \"pool/restricted\" {\n\tPackages \"dists/%s/restricted/binary-%s/Packages\";\n\tBinOverride \"%s/override.%s.restricted\";\n};\n\nDefault {\n\tPackages {\n\t\tExtensions \".deb\";\n\t\tCompress \". gzip\";\n\t};\n};\n\nContents {\n\tCompress \"gzip\";\n};\n ' % (self.__iso_fs_dir, distro_codename, distro_arch, index_dir, distro_codename, index_dir, distro_codename, distro_codename, distro_arch, index_dir, distro_codename))
                    f.close()
                    # create apt-ftparchive-udeb.conf
                    f = open(os.path.join(ftparchive_dir, 'apt-ftparchive-udeb.conf'), 'w')
                    f.write('Dir {\n\tArchiveDir \"%s/\";\n};\n\nTreeDefault {\n\tDirectory \"pool/\";\n};\n\nBinDirectory \"pool/main\" {\n\tPackages \"dists/%s/main/debian-installer/binary-%s/Packages\";\n\tBinOverride \"%s/override.%s.main.debian-installer\";\n};\n\nBinDirectory \"pool/restricted\" {\n\tPackages \"dists/%s/restricted/debian-installer/binary-%s/Packages\";\n\tBinOverride \"%s/override.%s.restricted.debian-installer\";\n};\n\nDefault {\n\tPackages {\n\t\tExtensions \".udeb\";\n\t\tCompress \". gzip\";\n\t};\n};\n\nContents {\n\tCompress \"gzip\";\n};\n ' % (self.__iso_fs_dir, distro_codename, distro_arch, index_dir, distro_codename, distro_codename, distro_arch, index_dir, distro_codename ))
                    f.close()
                    # create apt-ftparchive-extras.conf
                    f = open(os.path.join(ftparchive_dir, 'apt-ftparchive-extras.conf'), 'w')
                    f.write('Dir {\n\tArchiveDir \"%s/\";\n};\n\nTreeDefault {\n\tDirectory \"pool/\";\n};\n\nBinDirectory \"pool/extras\" {\n\tPackages \"dists/%s/extras/binary-%s/Packages\";\n};\n\nDefault {\n\tPackages {\n\t\tExtensions \".deb\";\n\t\tCompress \". gzip\";\n\t};\n};\n\nContents {\n\tCompress \"gzip\";\n};\n' % (self.__iso_fs_dir, distro_codename, distro_arch ))
                    f.close()
                    # create release.conf
                    f = open(os.path.join(ftparchive_dir, 'release.conf'), 'w')
                    f.write('APT::FTPArchive::Release::Origin \"Ubuntu\";\nAPT::FTPArchive::Release::Label \"Ubuntu\";\nAPT::FTPArchive::Release::Suite \"%s\";\nAPT::FTPArchive::Release::Version \"%s\";\nAPT::FTPArchive::Release::Codename \"%s\";\nAPT::FTPArchive::Release::Architectures \"%s\";\nAPT::FTPArchive::Release::Components \"main restricted extras\";\nAPT::FTPArchive::Release::Description \"Ubuntu %s\";\n' % (distro_codename, distro_version, distro_codename, distro_arch, distro_version))
                    f.close()

                    # create repo
                    self.log.info('Creating repository...')
                    ftparchive_conf_file = os.path.join(ftparchive_dir, 'release.conf')
                    p = subprocess.Popen('apt-ftparchive -c %s generate %s/apt-ftparchive-deb.conf' % (ftparchive_conf_file, ftparchive_dir), shell=True)
                    os.waitpid(p.pid, 0)
                    p = subprocess.Popen('apt-ftparchive -c %s generate %s/apt-ftparchive-udeb.conf' % (ftparchive_conf_file, ftparchive_dir), shell=True)
                    os.waitpid(p.pid, 0)
                    p = subprocess.Popen('apt-ftparchive -c %s generate %s/apt-ftparchive-extras.conf' % (ftparchive_conf_file, ftparchive_dir), shell=True)
                    os.waitpid(p.pid, 0)
                    p = subprocess.Popen('apt-ftparchive -c %s release %s/dists/%s > %s/dists/%s/Release' % (ftparchive_conf_file, self.__iso_fs_dir, distro_codename, self.__iso_fs_dir, distro_codename), shell=True)
                    os.waitpid(p.pid, 0)
                    # sign release
                    self.log.debug('Signing Release...')
                    release_gpg_file = os.path.join(self.__iso_fs_dir, 'dists' + os.sep + distro_codename + os.sep + 'Release.gpg')
                    # remove existing release
                    if os.path.exists(release_gpg_file):
                        os.remove(release_gpg_file)
                    p = subprocess.Popen('gpg --default-key \"%s\" --output %s/dists/%s/Release.gpg -ba %s/dists/%s/Release' % (key_name, self.__iso_fs_dir, distro_codename, self.__iso_fs_dir, distro_codename), shell=True)
                    os.waitpid(p.pid, 0)
                    # cleanup
                    shutil.rmtree(tmp_dir)
                    return True
            else:
                self.log.error('Unsupported build type: %s' % (self.__build_type))
        except Exception, d:
            self.log.error('Error adding packages: %s' % (d))
            return False
        
    def remove_packages(self, packages=None):
        try:
            if len(packages) > 0:
                pkg_list = ''
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
                f.write('#!/bin/sh\n# Reconstructor package removal script\n\nDEBIAN_FRONTEND=noninteractive apt-get -f -y --force-yes --purge remove %s\n\napt-get -f -y autoremove\napt-get clean\napt-get autoclean\n\n' % (pkg_list))
                f.close()
                # make script executable
                os.chmod(scr_file, 0775)
                self.log.debug('Package removal list: %s' % (pkg_list))
                # remove
                p = subprocess.Popen('chroot %s /tmp/pkgs.sh' % (self.__live_fs_dir), shell=True)
                os.waitpid(p.pid, 0)
                # cleanup
                os.remove(os.path.join(os.path.join(self.__live_fs_dir, 'tmp'), 'pkgs.sh'))
            return True
        except Exception, e:
            self.log.error('Error removing packages: %s' % (e))
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
    
    
    
    
    
    

