#!/usr/bin/env python
import os
import logging
import requests
import time
import sys
import reconstructor
try:
    import simplejson as json
except ImportError:
    import json

class BuildLogHandler(logging.Handler):
    def __init__(self, build_uuid=None, build_status_url=None, headers=None):
        logging.Handler.__init__(self)
        if not build_uuid or not build_status_url or not headers:
            raise NameError('You must specify a build_uuid, build_status_url and headers')
        self._build_uuid = build_uuid
        self._build_status_url = build_status_url
        self._headers = headers

    def emit(self, msg):
        try:
            print(msg.msg)
            data = {
                'uuid': self._build_uuid,
                'log': '{0} {1}: {2}'.format(msg.levelno, msg.name, msg.msg),
            }
            r = requests.post(self._build_status_url, data=json.dumps(data), headers=self._headers)
        except Exception, e:
            print(e)
            # ignore errors
            pass

class BuildServer(object):
    def __init__(self, app_url=None, key=None, output_dir=None, **kwargs):
        if not app_url or not key:
            raise RuntimeError('You must specify a Reconstructor url and key to use the build server')
        # check url
        if 'http' not in app_url:
            raise RuntimeError('You must specify either http:// or https:// in app_url')
        self._app_url = app_url
        self._key = key
        if not output_dir:
            self._output_dir = os.getcwd()
        else:
            self._output_dir = output_dir
        self._headers = {
            'X-BUILDSERVER-VERSION': reconstructor.__version__,
            'X-BUILDSERVER-KEY': key,
        }
        self._queue_url = '{0}/api/builds/next'.format(self._app_url)
        self._build_status_url = '{0}/api/builds/update'.format(self._app_url)
        self._log = logging.getLogger('buildserver')
        self._build_uuid = None
    

    def _update_build_status(self, status=None, result=''):
        try:
            data = {
                'uuid': self._build_uuid,
                'status': status,
                'result': result,
            }
            r = requests.post(self._build_status_url, data=json.dumps(data), headers=self._headers)
            if r.status_code != 200:
                self._log.warn('Unable to update build status: {0}'.format(json.loads(r.content)))
        except Exception, e:
            # ignore errors
            pass

    def start(self):
        self._log.debug('Using Reconstructor app at {0}'.format(self._app_url))
        self._log.debug('Output dir: {0}'.format(self._output_dir))
        self._log.info('Starting Build Server')
        try:
            while True:
                # get next build
                r = requests.get(self._queue_url, headers=self._headers)
                if r.status_code == 200:
                    build_data = json.loads(r.content)
                    self._log.debug(build_data)
                    self._build_uuid = build_data['uuid']
                    # setup custom logger
                    bl = logging.getLogger('build')
                    blh = BuildLogHandler(build_uuid=build_data['uuid'], \
                        build_status_url=self._build_status_url, headers=self._headers)
                    blh.setLevel(logging.DEBUG)
                    bl.addHandler(blh)
                    bl.info('Starting build')
                    self._update_build_status(status='running', result='Starting build')
                    time.sleep(5)
                    bl.info('Bootstrapping')
                    self._update_build_status(status='running', result='Bootstrapping')
                    time.sleep(5)
                    bl.info('Building ISO')
                    self._update_build_status(status='running', result='Building ISO')
                    time.sleep(5)
                    bl.info('Build complete')
                    self._update_build_status(status='complete', result='Build complete')
                    # reset build_uuid
                    self._build_uuid = None
                time.sleep(5)
        except KeyboardInterrupt:
            self._log.info('Stopping Build Server')
            sys.exit(0)
