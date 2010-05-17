#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
#    __init__.py   
#        Configuration module
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

from ConfigParser import ConfigParser
import os
import logging
import tempfile
import tarfile
import shutil
import imp

class Project(object):
    def __init__(self, filename=None):
        self._log = logging.getLogger('Project')
        self._filename = filename
        self._tmpdir = tempfile.mktemp()
        # project vars
        self.id = None
        self.name = None
        self.author = None
        self.version = None
        self.project_type = None
        self.distro = None
        self.environment = None
        self.post_script = None
        self.run_post_config = None
        self.arch = None
        self.distro_version = None
        self.src_iso = None
        self.output_file = None
        self.online = None
        self.job_id = None
        self.job_status_post_url = None
        self.packages = {}
        self.modules = []
        self.aws_cert = None
        self.aws_key = None
        self.aws_id = None
        self.aws_s3_bucket = None
        self.aws_s3_access_id = None
        self.aws_s3_access_key = None
        self.disk_image_type = None
        self.disk_image_size = None
        self.base_packages_removed = []
        # parse
        self.parse()
        # load packages
        self.load_packages()
        # load modules
        self.load_modules()

    # accessors
    def get_tmpdir(self): return self._tmpdir
    def get_filename(self): return self._filename
    def get_post_script(self): return os.path.join(self._tmpdir, 'post_script')

    def extract(self):
        if os.path.exists(self._filename):
            self._log.debug('Opening project...')
            t = tarfile.open(self._filename)
            t.extractall(self._tmpdir)
            return True
        else:
            self._log.error('Project file does not exist...')
            return False

    def load_packages(self):
        '''Loads packages from project'''
        pkg_file = os.path.join(self._tmpdir, 'packages')
        if os.path.exists(pkg_file):
            # parse packages
            f = open(os.path.join(pkg_file), 'r')
            pkgs = f.read().split('\n')
            f.close()
            for p in pkgs:
                if p != '':
                    pkg = p.split(' : ')
                    pkg_name = pkg[0].strip()
                    pkg_version = pkg[1].strip()
                    self.packages[pkg_name] = pkg_version
        else:
            log.warning('No package file in project...')
    
    def load_modules(self):
        self.modules = []
        mod_dir = 'modules'
        mod_path = os.path.join(self._tmpdir, mod_dir)
        # HACK: temporarily change path to load modules
        orig_path = os.getcwd()
        os.chdir(self._tmpdir)
        self._log.debug('Module dir: %s' % (mod_dir))
        self._log.debug('Modules: %s' % (os.listdir(mod_path)))
        for f in os.listdir(mod_path):
            try:
                if not f.startswith('__init__'):
                    t, filename, desc = imp.find_module(os.path.splitext(os.path.basename(f))[0], ['modules'])
                    m = imp.load_module(os.path.splitext(os.path.basename(f))[0], t, filename, desc)
                    if m not in self.modules:
                        self.modules.append(m)
                        self._log.info('Loaded module: %s' % (f))
            except Exception, d:
                self._log.error('Error loading module %s: %s' % (f, d))
        # change back to original dir
        os.chdir(orig_path)
        self._log.debug('Modules loaded: %s' % (self.modules))

    def cleanup(self):
        self._log.info('Cleaning up temporary project files...')
        if os.path.exists(self._tmpdir):
            shutil.rmtree(self._tmpdir)

    def parse(self):
        # extract project
        self.extract()
        # parse
        self._log.debug('Reading project info file...')
        prj_file = os.path.join(self._tmpdir, 'project_info')
        if os.path.exists(prj_file):
            cfg = ConfigParser()
            cfg.read(prj_file)
            if cfg.has_section('project'):
                self.id = cfg.get('project', 'id')
                self.name = cfg.get('project', 'name')
                self.author = cfg.get('project', 'author')
                self.aws_cert = cfg.get('project', 'aws_cert')
                self.aws_key = cfg.get('project', 'aws_key')
                self.aws_id = cfg.get('project', 'aws_id')
                self.aws_s3_bucket = cfg.get('project', 'aws_s3_bucket')
                self.aws_s3_access_id = cfg.get('project', 'aws_s3_access_id')
                self.aws_s3_access_key = cfg.get('project', 'aws_s3_access_key')
                self.version = cfg.get('project', 'version')
                self.distro = cfg.get('project', 'distro')
                self.environment = cfg.get('project', 'environment')
                self.project_type = cfg.get('project', 'project_type')
                self.arch = cfg.get('project', 'arch')
                self.distro_version = cfg.get('project', 'distro_version')
                self.src_iso = cfg.get('project', 'src_iso')
                if cfg.has_option('project', 'base_packages_removed'):
                    base_packages_removed = cfg.get('project', 'base_packages_removed')
                    self.base_packages_removed = base_packages_removed.split(',')
                if cfg.get('project', 'disk_image_type') != '':
                    self.disk_image_type = cfg.get('project', 'disk_image_type')
                if cfg.get('project', 'disk_image_size') != '':
                    self.disk_image_size = cfg.get('project', 'disk_image_size')
                self.output_file = cfg.get('project', 'output_file')
                if cfg.get('project', 'online').lower() == 'true':
                    self.online = True
                else:
                    self.online = False
                if cfg.get('project', 'run_post_config').lower() == 'true':
                    self.run_post_config = True
                else:
                    self.run_post_config = False
            if cfg.has_section('job'):
                self.job_id = cfg.get('job', 'id')
                self.job_status_post_url = cfg.get('job', 'post_url')
            # load packages
            return True
        else:
            self._log.error('Corrupt project.  Unable to load project info file.')
            return False
