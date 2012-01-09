#!/usr/bin/env python
import os
import logging
import tempfile
import shutil
from subprocess import Popen, PIPE, call
import errno
import time

class BaseDistro(object):
    def __init__(self):
        self._build_dir = tempfile.mkdtemp()
        self._copyright = 'Reconstructor (c) Lumentica, 2011'
        self._log = logging.getLogger('base')

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

    def _post_build(self):
        self._log.debug('post_build')

    def cleanup(self):
        self._log.debug('cleanup')
        if os.path.exists(self._build_dir):
            shutil.rmtree(self._build_dir)
