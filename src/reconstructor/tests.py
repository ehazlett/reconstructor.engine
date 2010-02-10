#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
#    tests.py   
#        Tests for Reconstructor
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


import unittest
import os
import stat
import sys
# set path
sys.path.append(os.path.dirname(os.getcwd()))    
#import settings
import logging
import tempfile
import shutil
from optparse import OptionParser
from reconstructor.core import fs_tools
from reconstructor.core import iso_tools
from reconstructor.core import squash_tools
from reconstructor.config import Project
from reconstructor.engine import BuildEngine

class TestBuildEngine(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = os.path.join(tempfile.gettempdir(), 'r_test')
        self.src_iso = os.path.join(os.path.join(os.getcwd(), 'test'), 'test.iso')
        self.squash_fs = os.path.join(os.path.join(os.getcwd(), 'test'), 'squash_test.squashfs')
        self.test_file = os.path.join(os.path.join(os.getcwd(), 'test'), 'test.txt')
        self.test_dir = os.path.join(os.path.join(os.getcwd(), 'test'), 'test_dir/')
        self.output_file = os.path.join(self.tmp_dir, 'custom.iso')
        self.engine = BuildEngine(distro='ubuntu', arch='x86', working_dir=self.tmp_dir, src_iso_filename=self.src_iso, output_file=self.output_file)
        self.engine.extract_iso()
        
    def testExtractIso(self):
        # assert iso extracts
        self.assertTrue(self.engine.extract_iso(), 'Error extracting iso...')
        self.assert_(os.listdir(self.engine.get_work_dir()) != 0, 'Error extracting ISO...')
    
    def testCreateIso(self):
        self.assertTrue(self.engine.extract_iso())
        self.assert_(self.engine.create_iso())
        self.assert_(os.path.exists(self.engine.get_output_filename()))
        os.system('cp %s /home/ehazlett/sort/' % (self.output_file))

    def testExtractLiveSquashFs(self):
        # assert squash extracts
        self.assertTrue(self.engine.extract_live_fs(), 'Error extracting squash filesystem...')
        self.assert_(os.listdir(self.engine.get_live_fs_dir()) != 0, 'Error extracting squash filesystem...')
        
    def testBuildLiveSquashFs(self):
        # assert squash fs is built
        self.assertTrue(self.engine.extract_live_fs(), 'Error extracting live filesystem...')
        self.assertTrue(self.engine.build_live_fs())
        self.assertTrue(os.path.exists(self.engine.get_live_fs_filename()), 'Live Filesystem does not exist...')
        
    def _testAddToFs(self):
        self.assertTrue(self.engine.add_to_target(self.test_file, '/opt', True), 'Error copying file...')
        self.assertTrue(os.path.exists(self.engine.get_live_fs_dir() + '/opt/' + os.path.basename(self.test_file)), 'File not copied...')
        self.assertTrue(self.engine.add_to_target(self.test_dir, '/opt', True), 'Error copying directory...')
        self.assertTrue(os.path.exists(self.engine.get_live_fs_dir() + '/opt/' + self.test_dir.split('/')[-2]), 'Directory not copied...')
    
    def testAddProjectData(self):
        p = Project(os.path.join(os.path.join(os.getcwd(), 'test'), 'test_project.rpj'))
        self.engine.set_project(p)
        self.assertTrue(self.engine.add_project_data())
        self.assertTrue(os.path.exists(os.path.join(os.path.join(self.engine.get_live_fs_dir(), 'opt'), 'testfile')))

    def tearDown(self):
        try:
            if os.path.exists(self.tmp_dir): shutil.rmtree(self.tmp_dir)
            self.assertFalse(os.path.exists(self.tmp_dir), 'Temporary directory not removed: %s' % (self.tmp_dir))
        except Exception, d:
            # ignore cleanup errors
            print('Unable to cleanup from TestBuilder.tearDown: %s' % (d))
            
class TestFsTools(unittest.TestCase):
    def setUp(self):
        self.iso = os.path.join(os.path.join(os.getcwd(), "test"), "test.iso")
        self.tmp_dir = os.path.join(tempfile.gettempdir(), 'r_test_mnt')
        if not os.path.exists(self.tmp_dir): os.makedirs(self.tmp_dir)
        
    def testMount(self):
        self.assertTrue(fs_tools.mount(self.iso, self.tmp_dir))
        self.assert_(os.listdir(self.tmp_dir) != 0)
        self.assertTrue(fs_tools.unmount(self.tmp_dir))
        
    def testUnmount(self):
        self.assertTrue(fs_tools.mount(self.iso, self.tmp_dir))
        self.assertTrue(fs_tools.unmount(self.tmp_dir))
        self.assertFalse(os.path.exists(self.tmp_dir))
        
    def tearDown(self):
        try:
            # cleanup
            if os.path.exists(self.tmp_dir): shutil.rmtree(self.tmp_dir)
        except Exception, d:
            print('Unable to cleanup from TestFsTools.tearDown: %s' % (d))

class TestSquashTools(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = os.path.join(tempfile.gettempdir(), 'r_test_squash')
        self.tmp_squash_dir = os.path.join(tempfile.gettempdir(), 'r_tmp_squash')
        self.squash_file = os.path.join(self.tmp_dir, 'test.squashfs')
        self.squash_root = os.path.join(self.tmp_dir, 'root')
        if not os.path.exists(self.tmp_dir): os.makedirs(self.tmp_dir)
        if not os.path.exists(self.squash_root): os.makedirs(self.squash_root)
        if not os.path.exists(os.path.join(self.squash_root, 'test')): os.makedirs(os.path.join(self.squash_root, 'test'))
    
    def testCreateSquashFs(self):
        self.assertTrue(squash_tools.create_squash_fs(source_dir=self.squash_root, dest_filename=self.squash_file, overwrite=True))
        self.assertTrue(os.path.exists(self.squash_file), 'Squash file does not exist...')
        self.assertTrue(len(self.squash_file) != 0)
        
    def testExtractSquashFs(self):
        self.assertTrue(squash_tools.create_squash_fs(source_dir=self.squash_root, dest_filename=self.squash_file, overwrite=True))
        self.assertTrue(squash_tools.extract_squash_fs(filename=self.squash_file, dest_dir=self.tmp_squash_dir), 'Error extracting squash filesystem...')
        self.assertTrue(os.listdir(self.tmp_squash_dir) != 0, 'Error extracting squash filesystem: directory empty...')
        
    def tearDown(self):
        try:
            if os.path.exists(self.tmp_dir): 
                shutil.rmtree(self.tmp_dir)
            if os.path.exists(self.tmp_squash_dir):
                shutil.rmtree(self.tmp_squash_dir)
        except Exception, d:
            print('Unable to cleanup from TestSquashTools.tearDown: %s' % (d))


class TestIsoTools(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = os.path.join(tempfile.gettempdir(), 'r_test_iso')
        self.iso_file = os.path.join(os.path.join(os.getcwd(), 'test'), 'test.iso')
        if not os.path.exists(self.tmp_dir): os.makedirs(self.tmp_dir)

    def testIsoExtract(self):
        tmp_iso_dir = os.path.join(self.tmp_dir, 'iso')
        os.makedirs(tmp_iso_dir)
        self.assert_(iso_tools.extract(self.iso_file, tmp_iso_dir))
        self.assert_(os.listdir(tmp_iso_dir))

    def testUpdateMd5(self):
        tmp_iso_dir = os.path.join(self.tmp_dir, 'iso')
        os.makedirs(tmp_iso_dir)
        self.assert_(iso_tools.extract(self.iso_file, tmp_iso_dir))
        self.assert_(os.listdir(tmp_iso_dir))
        self.assert_(iso_tools.update_md5sums(tmp_iso_dir), 'Error updating md5sums...')
        self.assert_(os.path.exists(os.path.join(tmp_iso_dir, 'md5sum.txt')), 'md5sum.txt does not exist...')

    def testAddId(self):
        tmp_iso_dir = os.path.join(self.tmp_dir, 'iso')
        os.makedirs(tmp_iso_dir)
        self.assert_(iso_tools.extract(self.iso_file, tmp_iso_dir))
        self.assert_(iso_tools.add_id(tmp_iso_dir))
        self.assert_(os.path.exists(os.path.join(tmp_iso_dir, '.disc_id')))

    def testIsoX86Create(self):
        tmp_iso_dir = os.path.join(self.tmp_dir, 'iso')
        os.makedirs(tmp_iso_dir)
        self.assert_(iso_tools.extract(self.iso_file, tmp_iso_dir))
        self.assert_(iso_tools.create('x86', 'x86 Test', tmp_iso_dir, os.path.join(self.tmp_dir, 'test.iso')), 'Unable to create ISO...')
        self.assert_(os.path.exists(os.path.join(self.tmp_dir, 'test.iso')), 'ISO does not exist...')
        os.system('cp %s /home/ehazlett/' % (self.tmp_dir+'/test.iso'))

    def tearDown(self):
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

class TestConfig(unittest.TestCase):
    def setUp(self):
        self.project_file = os.path.join(os.path.join(os.getcwd(), 'test'), 'test_project.rpj')
        self.project = None

    def testLoadProject(self):
        self.project = Project(self.project_file)
        self.assert_(self.project.name, 'Project name null')
        self.assert_(self.project.author, 'Project author null')
        self.assert_(self.project.version, 'Project version null')
        self.assert_(self.project.distro, 'Project distro null')
        self.assert_(self.project.distro_version, 'Project distro_version null')
        self.assert_(self.project.arch, 'Project arch null')
        self.assert_(self.project.src_iso, 'Project src_iso null')
        self.assert_(self.project.output_file, 'Project output_file null')
        self.project.cleanup()
    
    def tearDown(self):
        pass

if __name__ == '__main__':
    # check for root privledges
    if os.getuid() == 0:
        LOG_LEVEL=logging.ERROR
        LOG_FILE='tests.log'
        LOG_CONFIG=logging.basicConfig(level=LOG_LEVEL,
                            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                            datefmt='%m-%d-%Y %H:%M:%S',
                            filename=LOG_FILE,
                            filemode='w')
                        
        # run tests
        unittest.main()
    else:
        print('You must be root to run...')
        
