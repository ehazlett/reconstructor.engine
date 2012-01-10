#!/usr/bin/env python
import os
import sys
import logging
import tempfile
import shutil
import traceback
from subprocess import Popen, PIPE, call
import errno
import time

class BaseDistro(object):
    def __init__(self):
        self._build_dir = tempfile.mkdtemp()
        self._copyright = 'Reconstructor (c) Lumentica, 2011'
        self._log = logging.getLogger('base')
        self._log.debug('Build dir: {0}'.format(self._build_dir))

    def _pre_build(self):
        self._log.debug('pre_build')

    def _run_command(self, command=''):
        return call(command, shell=True)
        p = Popen([command], shell=True, stdout=PIPE, stderr=PIPE)
        cur_line = None
        while True:
            try:
                out, err = p.communicate()
                o = out
                e = err
                self._log.debug(o)
                self._log.debug(e)
                time.sleep(1)
            except Exception, e:
                print(e)
                break
    

    def build(self):
        self._pre_build()
        self._build_distro()
        self._run_modules()
        self._post_build()

    def _run_modules(self):
        self._log.debug('run_modules')
        #cur_dir = os.getcwd()
        ## change to build dir
        #os.chdir(self._build_dir)
        sys.path.append(self._build_dir)
        mods = []
        if self._modules:
            self._log.info('Running modules')
            for mod in self._modules:
                self._log.debug(mod)
                try:
                    m = __import__('.'.join(mod['module'].split('.')[0:-1]))
                    self._log.debug(m)
                    x = getattr(m, '.'.join(mod['module'].split('.')[1:-1]))
                    self._log.debug(x)
                    kls = getattr(x, mod['module'].split('.')[-1])
                    self._log.debug(kls)
                except Exception, e:
                    self._log.error('Error loading module: {0}'.format(traceback.format_exc()))
                    continue
                try:
                    a = kls(chroot=os.path.join(self._build_dir, 'chroot'), \
                        build_dir=self._build_dir, **mod['options'])
                    self._log.info('Running module: {0}'.format(a))
                    a.run()
                    self._log.info('Module {0} complete'.format(a))
                except Exception, e:
                    self._log.error('Error running module: {0}'.format(traceback.format_exc()))

    def _post_build(self):
        self._log.debug('post_build')

    def cleanup(self):
        self._log.debug('cleanup')
        if os.path.exists(self._build_dir):
            shutil.rmtree(self._build_dir)
