#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
#    base.py   
#        Base distro module
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
import tarfile
import shutil
import logging
import time
import subprocess
import signal
import tempfile
import re
import commands
from reconstructor import settings
from reconstructor.core import iso_tools
from reconstructor.core import fs_tools

class BaseDistro(object):
    '''Base class for all distributions.'''
    def __init__(self, arch=None, working_dir=None, src_iso_filename=None, online=False, run_post_config=True, build_type=None):
        self.log = logging.getLogger('BaseDistro')
        self.__arch = arch
        self.__work_dir = working_dir
        self.__live_fs_dir = os.path.join(self.__work_dir, 'live_fs')
        self.__iso_fs_dir = os.path.join(self.__work_dir, 'iso_fs')
        self.__initrd_dir = os.path.join(self.__work_dir, 'initrd')
        self.__src_iso_filename = src_iso_filename
        self.__live_fs_filename = None
        self.__project_dir = None
        self.__online = online
        self.__run_post_config = run_post_config
        self.__build_type = build_type

    # accessors
    def get_arch(self): return self.__arch
    def get_online(self): return self.__online
    def get_run_post_config(self): return self.__run_post_config
    def get_work_dir(self): return self.__work_dir
    def get_live_fs_dir(self): return self.__live_fs_dir
    def get_iso_fs_dir(self): return self.__iso_fs_dir
    def get_initrd_dir(self): return self.__initrd_dir 
    def get_src_iso_filename(self): return self.__src_iso_filename 
    def get_live_fs_filename(self): return self.__live_fs_filename
    def get_project_dir(self): return self.__project_dir
    def get_project_files_dir(self): return os.path.join(self.__project_dir, 'files')
    def set_arch(self, newValue): self.__arch = newValue
    def set_work_dir(self, newValue): self.__work_dir = newValue
    def set_live_fs_dir(self, newValue): self.__live_fs_dir = newValue
    def set_iso_fs_dir(self, newValue): self.__iso_fs_dir = newValue
    def set_initrd_dir(self, newValue): self.__initrd_dir = newValue
    def set_project_dir(self, newValue): self.__project_dir = newValue
    def set_live_fs_filename(self, newValue): self.__live_fs_filename = newValue
    def get_build_type(self): return self.__build_type

    # methods
    def watch_process(self, process=None):
        if process:
            timeout = settings.SCRIPT_TIMEOUT
            cur = 0
            p = process
            self.log.debug('Watching script PID: %s, Timeout: %s' % (p.pid, timeout))
            while cur < timeout:
                try:
                    try:
                        os.kill(p.pid, 0)
                    except:
                        # not running; return
                        return True
                    if p.poll():
                        print('Process ended: %s' % (p.returncode))
                        return True
                    else:
                        cur += 1
                        time.sleep(1)
                except:
                    # ignore errors for now
                    return True
            try:
                # timeout occured; kill process and return
                self.log.error('Timeout running script.  Terminating...')
                os.kill(p.pid, signal.SIGTERM)
                return False
            except:
                return False

    def extract_iso_fs(self):
        '''Extracts contents of ISO file to self.__iso_fs_dir'''
        try:
            return iso_tools.extract(iso_filename=self.__src_iso_filename, target_dir=self.__iso_fs_dir)
        except Exception, d:
            self.log.error('Error extracting ISO: %s' % (d))
            return False
    
    def extract_live_fs(self):
        raise RuntimeError, "Not yet implemented..."
        
    def build_live_fs(self):
        raise RuntimeError, "Not yet implemented..."
    
    def build_ec2_ami(self):
        raise RuntimeError, "Not yet implemented..."

    def extract_initrd(self):
        raise RuntimeError, "Not yet implemented..."

    def build_initrd(self):
        raise RuntimeError, "Not yet implemented..."

    def add_package(self, package_name=None):
        '''Installs a package into the chroot environment'''
        raise RuntimeError, "Not yet implemented..."

    def add_packages(self, packages=None):
        '''Installs packages from project file into the chroot environment'''
        raise RuntimeError, "Not yet implemented..."

    def run_command(self, cmd=None):
        '''Runs command in chroot'''
        try:
            os.system('chroot %s %s' % (self.__live_fs_dir, cmd))
            return True
        except Exception, d:
            self.log.error('Error running command %s: %s' % (cmd, d))
            return False

    def run_modules(self, modules=None):
        for m in modules:
            try:
                self.log.debug('Running %s' % (m))
                x = m.Module()
                x.vars['distro'] = self
                x.run()
            except Exception, d:
                self.log.error('Error running %s: %s' % (m, d))

    def run_script(self, script_file=None):
        try:
            if os.path.exists(script_file):
                # check for zero length script
                f = open(script_file, 'r')
                if len(f.read()) > 0:
                    f.close()
                    # copy to chroot
                    dest_file = os.path.join(os.path.join(self.__live_fs_dir, 'tmp'), 'script')
                    shutil.copy(script_file, dest_file)
                    os.chmod(dest_file, 0775)
                    # try to parse script interpreter
                    f = open(dest_file, 'r')
                    s = f.read().split('\n')[0]
                    env = 'bash'
                    if s.lower().find('python') > -1:
                        env = 'python'
                        self.log.info('Using python for interpreter...')
                    elif s.lower().find('perl') > -1:
                        env = 'perl'
                        self.log.info('Using perl for interpreter...')
                    p = subprocess.Popen('chroot %s %s /tmp/script > %s/tmp/script.log' % (self.__live_fs_dir, env, self.__live_fs_dir), shell=True)
                    # watch script to make sure it doesn't halt for input, etc.
                    self.watch_process(p)
                    log_file = os.path.join(self.__live_fs_dir, 'tmp' + os.sep + 'script.log')
                    if os.path.exists(log_file):
                        f = open(log_file, 'r')
                        out = f.read()
                        f.close()
                        os.remove(log_file)
                        self.log.info('Script output: \n%s' % (out))
                    else:
                        self.log.warn('No script output...')
                    return True
                else:
                    f.close()
                    return True

            else:
                self.log.error('Script file %s does not exist...' % (dest_file))
                return False
        except Exception, d:
            self.log.error('Error running script: %s' % (d))
            return False
        
    def check_working_dirs(self):
        '''Checks to make sure working directories exist and creates if necessary'''
        self.log.debug('Checking working directories...')
        if not os.path.exists(self.__work_dir):
            # not found; create
            self.log.debug('Creating working directory: %s...' % (self.__work_dir))
            os.makedirs(self.__work_dir)
        #if not os.path.exists(self.__squashfs_dir):
        #    self.log.debug('Creating working directory: %s...' % (self.__squashfs_dir))
        #    os.makedirs(self.__squashfs_dir)
        #if not os.path.exists(self.__iso_fs_dir):
        #    self.log.debug('Creating working directory: %s...' % (self.__iso_fs_dir))
        #    os.makedirs(self.__iso_fs_dir)
        
    def set_gconf_value(self, key=None, key_type=None, value=None):
        '''Sets GConf key'''
        if key and key_type and value:
            self.log.info('Setting GConf: %s to %s' % (key, value))
            os.system('chroot \"%s\" gconftool-2 --direct --config-source xml:readwrite:/etc/gconf/gconf.xml.defaults --type %s --set %s \"%s\"' % (self.__live_fs_dir, key_type, key, value))
            return True
        else:
            self.log.error('You must specify a key, key type and value.')
            return False

    def extract_tar_application(self, source_filename=None, dest_dir=None):
        '''Extracts tar.gz or tar.bz2 into dest_dir under the squash filesystem'''
        try:
            if source_filename == None or dest_dir == None:
                self.log.error('Source filename and destination directory must not be null...')
                return False
            if not os.path.exists(source_filename):
                self.log.error('Source file %s does not exist...' % (source_filename))
                return False
            if not os.path.exists(dest_dir):
                self.log.error('Destination directory %s does not exists...' % (dest_dir))
                return False
            t = tarfile.open(source_filename, 'r')
            self.log.debug('Extracting %s to %s' % (source_filename, self.__live_fs_dir + dest_dir))
            t.extractall(path='%s' % (self.__live_fs_dir + dest_dir))
            t.close()
            return True    
        except Exception, d:
            self.log.error('Error installing tar application: %s' % (d))
            return False
            
    def add_to_target_fs(self, src=None, dest=None, overwrite=False):
        '''Adds files and directories to the target filesystem'''
        try:
            # check dirs
            if src == None or dest == None:
                self.log.error('Source and destination must not be null...')
                return False
            # check to make sure src exists
            if not os.path.exists(src):
                self.log.error('Source directory %s does not exist...' % (src))
                return False
            # is src a directory?
            if os.path.isdir(src):
                # check for trailing '/'
                if not src.endswith('/'):
                    src += '/'
                # check for existing and remove if necessary...
                if os.path.exists(self.__live_fs_dir + dest + os.sep + src.split('/')[-2]):
                    if overwrite:
                        self.log.warn('Removing existing destination directory: %s' % (self.__live_fs_dir + dest + os.sep + src.split('/')[-2]))
                        shutil.rmtree(self.__live_fs_dir + dest + os.sep + src.split('/')[-2])
                    else:
                        self.log.error('Destination directory %s exists; not overwriting...' % (self.__live_fs_dir + dest + os.sep + src.split('/')[-2]))
                        self.log.debug('  Use overwrite=True to overwrite...')
                        return False
                # copy
                self.log.info('Copying directory %s to %s' % (src, self.__live_fs_dir + dest))
                shutil.copytree(src, self.__live_fs_dir + dest + os.sep + src.split('/')[-2], True) # copy symlinks
                return True
            # is src a file?
            if os.path.isfile(src):
                # check for existing and remove if necessary...
                if os.path.exists(self.__live_fs_dir + dest): # make sure dest exists and is file (don't remove if a dir)
                    if os.path.isfile(self.__live_fs_dir + dest + os.sep + os.path.basename(src)):
                        if overwrite:
                            self.log.warn('Removing existing file: %s' % (self.__live_fs_dir + dest + os.sep + os.path.basename(src)))
                            os.remove(self.__live_fs_dir + dest + os.sep + os.path.basename(src))
                        else:
                            self.log.error('Destination file %s exists; not overwriting...' % (self.__live_fs_dir + dest + os.sep + os.path.basename(src)))
                            self.log.debug('  Use overwrite=True to overwrite...')
                            return False
                else:
                    self.log.warn('Destination directory %s does not exist; creating...' % (dest))
                    os.makedirs(self.__live_fs_dir + dest)
                # copy
                self.log.info('Copying file %s to %s' % (src, self.__live_fs_dir + dest))
                shutil.copy(src, self.__live_fs_dir + dest + '/')
                return True
        except Exception, d:
            self.log.error('Error copying %s to %s: %s' % (src, dest, d))
            return False
    
    def generate_password_script(self):
        scr = '# Reconstructor configuration script\n#\ncase \"$1\" in \n\tstart)\n\t\tif [ ! -f /usr/share/reconstructor/.config_run ]; then  echo \"* Please set the root password...\" ; passwd root ; mkdir -p /usr/share/reconstructor/ ; touch /usr/share/reconstructor/.config_run; fi\n\t;;\nesac\n'
        return scr

    def create_disk_image(self, size='10', dest_file=None, image_type=None, distro_name=None):
        if image_type == None:
            self.log.error('No image type specified for disk image.')
            return False
        if distro_name == None:
            self.log.error('No distro specified...')
            return False
        tmpdir = tempfile.mkdtemp()
        kpart = None
        img_name = dest_file
        distro = distro_name.lower()
        self.log.debug('Using %s distro...')
        try:
            f = open(os.path.join(self.__live_fs_dir, '.r_id'), 'w')
            f.write('Built using %s %s\n%s\n%s\n' % (settings.APP_NAME, settings.APP_VERSION, settings.APP_COPYRIGHT, settings.APP_URL))
            f.close()
            if size.find('.') > -1:
                size = str(int(float(round(float(size)))))
                if int(size) < 1:
                    size = '1'
            self.log.debug('Creating %s GB sparse image...' % (size))
            part_size = int(size)*1024
            os.system('dd if=/dev/zero of=%s bs=1M count=0 seek=%s' % (dest_file, str(part_size)))
            self.log.info('Building %s disk image...' % (image_type))
            # build based on type
            if image_type == 'qemu' or image_type == 'vmware':
                self.log.debug('Creating partition...')
                # create partition table
                os.system('parted -s %s mklabel msdos' % (dest_file))
                os.system('parted -s %s mkpartfs primary ext2 0 %s' % (dest_file, part_size))
                # set boot
                os.system('parted -s %s set 1 boot on' % (dest_file))
                # parse output from kpartx to get device
                rx = re.compile('.*loop(\d+)p')
                out = commands.getoutput('kpartx -av %s' % (dest_file))
                self.log.debug('Kpartx: %s' % (out))
                kpart = rx.match(out).group(1)
                if kpart:
                    # format partition
                    self.log.debug('Formatting partition...')
                    os.system('mkfs.ext3 -F /dev/mapper/loop%sp1' % (kpart))
                    # mount
                    self.log.debug('Using /dev/mapper/loop%sp1 for root...' % (kpart))
                    os.system('mount /dev/mapper/loop%sp1 %s/' % (kpart, tmpdir))
                    self.log.debug('Copying files...')
                    # copy files
                    os.system('rsync -a %s/ %s/' % (self.__live_fs_dir, tmpdir))
                    # create config script
                    self.log.debug('Creating configuration script...')
                    f = open(os.path.join(tmpdir, 'etc' + os.sep + 'rc2.d' + os.sep + 'S25reconstructor'), 'w')
                    f.write(self.generate_password_script())
                    f.close()
                    os.chmod(os.path.join(tmpdir, 'etc' + os.sep + 'rc2.d' + os.sep + 'S25reconstructor'), 0775)
                    # create fstab
                    self.log.debug('Creating /etc/fstab...')
                    f = open(os.path.join(tmpdir, 'etc' + os.sep + 'fstab'), 'w')
                    f.write('# fstab generated by Reconstructor\n#\n/dev/sda1\t/\text3\tdefaults\t1\t1\n')
                    f.close()
                    # create /boot/grub
                    os.makedirs(os.path.join(tmpdir, 'boot' + os.sep + 'grub'))
                    # create device.map
                    f = open(os.path.join(tmpdir, 'boot' + os.sep + 'grub' + os.sep + 'device.map'), 'w')
                    f.write('(hd0)\t/dev/sda\n')
                    f.close()
                    # install grub
                    # HACK: copy the files needed for grub
                    gdir = '/usr/lib/grub/' + os.listdir('/usr/lib/grub')[0]
                    grub_dest_dir = os.path.join(tmpdir, 'boot' + os.sep + 'grub')
                    for f in os.listdir(gdir):
                        shutil.copy(os.path.join(gdir, f), os.path.join(grub_dest_dir, f))
                    # run grub
                    os.system('chroot %s update-grub -y' % (tmpdir))
                    # install bootloader
                    os.system('grub --batch --device-map=/dev/null <<EOF\ndevice (hd0) %s\nroot (hd0,0)\nsetup (hd0)\nquit\nEOF' % (dest_file))
    
                else:
                    self.log.error('Cannot find mounted partition (kpartx)...')
                    return False
            elif image_type == 'xen':
                self.log.debug('Formatting image...')
                os.system('mkfs.ext3 -F %s' % (dest_file))
                # mount
                os.system('mount -o loop %s %s/' % (dest_file, tmpdir))
                self.log.debug('Copying files...')
                # copy files
                os.system('rsync -a %s/ %s/' % (self.__live_fs_dir, tmpdir))
            elif image_type == 'live':
                self.log.debug('Creating partition...')
                # create partition table
                os.system('parted -s %s mklabel msdos' % (dest_file))
                os.system('parted -s %s mkpartfs primary fat32 0 %s' % (dest_file, part_size))
                # set boot
                os.system('parted -s %s set 1 boot on' % (dest_file))
                # parse output from kpartx to get device
                rx = re.compile('.*loop(\d+)p')
                out = commands.getoutput('kpartx -av %s' % (dest_file))
                self.log.debug('Kpartx: %s' % (out))
                kpart = rx.match(out).group(1)
                if kpart:
                    # format partition
                    self.log.debug('Formatting partition...')
                    os.system('mkfs.vfat /dev/mapper/loop%sp1' % (kpart))
                    # mount
                    self.log.debug('Using /dev/mapper/loop%sp1 for root...' % (kpart))
                    os.system('mount /dev/mapper/loop%sp1 %s/' % (kpart, tmpdir))
                    self.log.debug('Copying files...')
                    # copy files
                    os.system('rsync -a --ignore-errors --force %s/ %s/' % (self.__iso_fs_dir, tmpdir))
                    # configure syslinux
                    self.log.info('Setting up syslinux configuration...')
                    # check for existing syslinux
                    shutil.move(os.path.join(tmpdir, 'isolinux'), os.path.join(tmpdir, 'syslinux'))
                    shutil.move(os.path.join(tmpdir, 'syslinux' + os.sep + 'isolinux.cfg'), os.path.join(tmpdir, 'syslinux' + os.sep + 'syslinux.cfg'))
                    # syslinux.cfg configuration
                    if distro == 'ubuntu':
                        syslinux_cfg = "DEFAULT /casper/vmlinuz\nAPPEND  noprompt cdrom-detect/try-usb=true persistent file=/cdrom/preseed/ubuntu.seed boot=casper initrd=/casper/initrd.gz quiet splash --\nTIMEOUT 10\nPROMPT 1\n"
                    elif distro == 'debian':
                        syslinux_cfg = "DEFAULT /live/vmlinuz1\nAPPEND  initrd=/live/initrd1.img boot=live union=aufs --\nTIMEOUT 10\nPROMPT 1\n"
                    #TODO: add fedora support?
                    # write syslinux.cfg
                    try:
                        sys_cfg_filename = '%s/syslinux/syslinux.cfg' % (tmpdir)
                        self.log.debug('Writing configuration to syslinux.cfg...')
                        f_sys_cfg = open(sys_cfg_filename, 'w')
                        f_sys_cfg.write(syslinux_cfg)
                        f_sys_cfg.close()
                    except Exception, d:
                        self.log.error('Error writing syslinux configuration: %s' % (d))
                    # run syslinux
                    self.log.info('Running syslinux...')
                    os.system('syslinux -f /dev/mapper/loop%sp1' % (kpart))
                    # install mbr
                    self.log.info('Installing MBR...')
                    os.system('install-mbr %s' % (dest_file))

        except Exception, d:
            self.log.error(d)
        finally:
            # unmount
            os.system('umount %s' % (tmpdir))
            # cleanup
            os.system('kpartx -d %s' % (dest_file))
            os.system('rmdir %s' % (tmpdir))
            # check for vmware -- convert img
            if image_type == 'vmware':
                self.log.info('Converting to VMware image...')
                os.system('qemu-img convert %s -O vmdk %s.vmdk' % (dest_file, dest_file.split('.')[0]))
                img_name = dest_file.split('.')[0]+'.vmdk'
            return img_name.split('/')[-1]
