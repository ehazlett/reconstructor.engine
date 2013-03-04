#!/usr/bin/env python
# Copyright (c) 2013 Evan Hazlett
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import os
from base import BaseDistro
from subprocess import Popen, PIPE, STDOUT
import logging
import shutil

class Ubuntu(BaseDistro):
    """
    Core distro class

    """
    def __init__(self, *args, **kwargs):
        super(Ubuntu, self).__init__(*args, **kwargs)
        self.log = logging.getLogger('distro.ubuntu')

    def setup(self):
        self.log.debug('Name: {0}'.format(self._name))
        self.log.debug('Codename: {0}'.format(self._codename))
        self.log.debug('Architecture: {0}'.format(self._arch))
        self.log.debug('Working directory: {0}'.format(self._work_dir))
        self.log.info('Setting up base distro environment')
        cmd = "debootstrap --arch={0} --exclude=atd {1} {2}".format(self._arch,
            self._codename, self._chroot_dir)
        self._run_command(cmd)
        self._mount_dev()
        self._setup_network()
        self._setup_apt()
        self._setup_machine()
        self._setup_iso_dir()
        self._install_extra_packages()

    def _mount_dev(self):
        self.log.debug('Mounting filesystems')
        cmd = "mount --bind /dev {0}/dev".format(self._chroot_dir)
        self._run_command(cmd)
        cmd = "mkdir -p /proc ; mount none -t proc /proc"
        self._run_chroot_command(cmd)
        cmd = "mount none -t sysfs /sys"
        self._run_chroot_command(cmd)
        cmd = "mount none -t devpts /dev/pts"
        self._run_chroot_command(cmd)

    def _setup_network(self):
        self.log.debug('Setting up hosts and DNS resolving')
        cmd = "cp /etc/hosts {0}/etc/".format(
            self._chroot_dir)
        self._run_command(cmd)
        cmd = "cp /etc/resolv.conf {0}/etc/".format(
            self._chroot_dir)
        self._run_command(cmd)

    def _setup_apt(self):
        self.log.debug('Setting up APT')
        tmpl = """deb http://us.archive.ubuntu.com/ubuntu/ {0} main
deb-src http://us.archive.ubuntu.com/ubuntu/ {0} main
deb http://us.archive.ubuntu.com/ubuntu/ {0} universe
deb-src http://us.archive.ubuntu.com/ubuntu/ {0} universe
deb http://us.archive.ubuntu.com/ubuntu/ {0} multiverse
deb-src http://us.archive.ubuntu.com/ubuntu/ {0} multiverse
deb http://us.archive.ubuntu.com/ubuntu/ {0} restricted
deb-src http://us.archive.ubuntu.com/ubuntu/ {0} restricted
""".format(self._codename)
        cmd = 'echo "{0}" > {1}/etc/apt/sources.list'.format(tmpl,
            self._chroot_dir)
        self._run_command(cmd)
        self._run_chroot_command('apt-get update')

    def _setup_machine(self):
        self.log.debug('Configuring machine id')
        # setup machine id
        cmd = "dbus-uuidgen > /var/lib/dbus/machine-id"
        self._run_chroot_command(cmd)
        cmd = "mv /sbin/initctl /sbin/initctl.bkup"
        self._run_chroot_command(cmd)
        cmd = "ln -sf /bin/true /sbin/initctl"
        self._run_chroot_command(cmd)
        open('{0}/etc/hostname'.format(self._chroot_dir), 'w').write(
            self._hostname)
        # policy file to prevent daemons from starting
        policy_file = '{0}/usr/sbin/policy-rc.d'.format(self._chroot_dir)
        with open(policy_file, 'w') as f:
            f.write('#!/bin/sh\nexit 101\n')
        os.chmod(policy_file, 0755)
        # install dbus
        self.add_packages(['dbus'])
        # install packages for live env
        self.add_packages(['ubuntu-minimal', 'casper', 'psmisc'])
        self.add_packages(['discover', 'laptop-detect', 'os-prober'])
        self.log.debug('-----MARK-----')
        # set grub-pc selections for automated
        grub_pc_selections = """grub-pc grub-pc/kopt_extracted  boolean false
grub-pc grub2/kfreebsd_cmdline  string
grub-pc grub2/device_map_regenerated    note
grub-pc grub-pc/install_devices	multiselect /dev/sda
grub-pc grub-pc/postrm_purge_boot_grub  boolean false
grub-pc grub-pc/install_devices_failed_upgrade  boolean true
grub-pc grub2/linux_cmdline string
grub-pc grub-pc/install_devices_empty   boolean false
grub-pc grub2/kfreebsd_cmdline_default  string  quiet
grub-pc grub-pc/install_devices_failed  boolean false
grub-pc grub-pc/install_devices_disks_changed   multiselect
grub-pc grub2/linux_cmdline_default string  quiet
grub-pc grub-pc/chainload_from_menu.lst boolean true
grub-pc grub-pc/hidden_timeout  boolean true
grub-pc grub-pc/mixed_legacy_and_grub2  boolean true
grub-pc grub-pc/timeout string  10"""
        tmpfile_name = '/tmp/grub_pc.debconf'
        tmpfile = '{0}{1}'.format(self._chroot_dir, tmpfile_name)
        with open(tmpfile, 'w') as f:
            f.write(grub_pc_selections)
        cmd = "cat {0} | debconf-set-selections".format(tmpfile_name)
        self._run_chroot_command(cmd)
        self.add_packages(['grub2', 'grub-pc'])
        self.add_packages(['linux-image-generic'])

    def _setup_iso_dir(self):
        dirs = ['casper', 'isolinux', 'install', '.disk']
        for d in dirs:
            fdir = os.path.join(self._iso_dir, d)
            if not os.path.exists(fdir):
                os.makedirs(fdir)
        # copy kernel and initrd
        cmd = "cp {0}/boot/vmlinuz-*.*.*-**-generic {1}/casper/vmlinuz".format(
            self._chroot_dir, self._iso_dir)
        self._run_command(cmd)
        cmd = "cp {0}/boot/initrd.img-*.*.*-**-generic {1}/casper/initrd.img".format(
            self._chroot_dir, self._iso_dir)
        self._run_command(cmd)
        cmd = "cp /usr/lib/syslinux/isolinux.bin {1}/isolinux/".format(
            self._chroot_dir, self._iso_dir)
        self._run_command(cmd)
        cmd = "echo \"***** Live CD *****\" > {0}/isolinux/isolinux.txt".format(
            self._iso_dir)
        self._run_command(cmd)
        boot_tmpl = """DEFAULT live
LABEL live
  menu label ^Start or install Ubuntu Remix
  kernel /casper/vmlinuz
  append  file=/cdrom/preseed/ubuntu.seed boot=casper initrd=/casper/initrd.img quiet splash --
LABEL check
  menu label ^Check CD for defects
  kernel /casper/vmlinuz
  append  boot=casper integrity-check initrd=/casper/initrd.img quiet splash --
LABEL hd
  menu label ^Boot from first hard disk
  localboot 0x80
  append -
DISPLAY isolinux.txt
TIMEOUT 300
PROMPT 1
"""
        tmpfile = '{0}/isolinux/isolinux.cfg'.format(self._iso_dir)
        with open(tmpfile, 'w') as f:
            f.write(boot_tmpl)
        cmd = "chroot {0} dpkg-query -W --showformat='${{Package}} ${{Version}}\n' | sudo tee {1}/casper/filesystem.manifest".format(self._chroot_dir, self._iso_dir)
        self._run_command(cmd)
        cmd = "cp -v {0}/casper/filesystem.manifest {0}/casper/filesystem.manifest-desktop".format(
            self._iso_dir)
        self._run_command(cmd)

    def _install_extra_packages(self):
        if self._packages:
            self.log.info('Installing extra packages')
            self.log.debug('Packages: {0}'.format(','.join(self._packages)))
            self.add_packages(self._packages)

    def _teardown_machine(self):
        self.log.debug('Removing machine id')
        cmd = "rm -f /var/lib/dbus/machine-id"
        self._run_chroot_command(cmd)
        self.log.debug('Removing initctl diversion')
        cmd = "rm /sbin/initctl"
        self._run_chroot_command(cmd)
        cmd = "mv /sbin/initctl.bkup /sbin/initctl"
        self._run_chroot_command(cmd)
        policy_file = '{0}/usr/sbin/policy-rc.d'.format(self._chroot_dir)
        os.remove(policy_file)

    def _teardown_network(self):
        self.log.debug('Removing network config')
        cmd = "rm -rf {0}/etc/hosts".format(
            self._chroot_dir)
        self._run_chroot_command(cmd)
        cmd = "rm -rf {0}/etc/resolv.conf".format(
            self._chroot_dir)
        self._run_chroot_command(cmd)

    def _unmount_dev(self):
        self.log.debug('Stopping processes in chroot')
        cmd = "fuser -k {0}/".format(self._chroot_dir)
        self._run_command(cmd)
        self.log.debug('Unmounting filesystems')
        cmd = "umount -lf /proc"
        self._run_chroot_command(cmd)
        cmd = "umount -lf /sys"
        self._run_chroot_command(cmd)
        cmd = "umount -lf /dev/pts"
        self._run_command(cmd)
        cmd = "umount -lf {0}/dev".format(self._chroot_dir)
        self._run_command(cmd)

    def add_packages(self, packages=[]):
        pkg_list = ' '.join(packages)
        cmd = "LC_ALL=C DEBIAN_PRIORITY=critical DEBCONF_FRONTEND=noninteractive apt-get install -y --force-yes {0}".format(
            pkg_list)
        self._run_chroot_command(cmd)

    def build(self):
        self.log.info('Building Live Filesystem ; this will take a while')
        squashfs_file = os.path.join(self._iso_dir, 'casper/filesystem.squashfs')
        if os.path.exists(squashfs_file):
            os.remove(squashfs_file)
        cmd = "mksquashfs {0} {1}/casper/filesystem.squashfs".format(
            self._chroot_dir, self._iso_dir)
        self._run_command(cmd)
        cmd = "printf $(sudo du -sx --block-size=1 {0} | cut -f1) > {1}/casper/filesystem.size".format(
            self._chroot_dir, self._iso_dir)
        self._run_command(cmd)
        defines_tmpl = """#define DISKNAME  {0}
#define TYPE  binary
#define TYPEbinary  1
#define ARCH  {1}
#define ARCH{1}  1
#define DISKNUM  1
#define DISKNUM1  1
#define TOTALNUM  0
#define TOTALNUM0  1
""".format(self._name, self._arch)
        defines_file = os.path.join(self._iso_dir, 'README.diskdefines')
        with open(defines_file, 'w') as f:
            f.write(defines_tmpl)
        # disk info
        open(os.path.join(self._iso_dir, '.disk/base_installable'), 'w').write('')
        open(os.path.join(self._iso_dir, '.disk/cd_type'), 'w').write(
            'full_cd/single')
        open(os.path.join(self._iso_dir, '.disk/info'), 'w').write(
            self._name)
        open(os.path.join(self._iso_dir, '.disk/release_notes_url'), 'w').write(
            self._url)
        # generate md5s
        cmd = "(cd {0} ; find . -type f -print0 | xargs -0 md5sum | grep -v \"\./md5sum.txt\" > md5sum.txt)".format(self._iso_dir)
        self._run_command(cmd)
        cmd = "cd {0} ; mkisofs -r -V \"{1}\" -cache-inodes -J -l -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -o \"{2}\" .".format(
            self._iso_dir, self._name, self._output_file)
        self._run_command(cmd)

    def run_chroot_script(self):
        raise NotImplementedError
    
    def teardown(self):
        self._teardown_network()
        self._teardown_machine()
        self._unmount_dev()
