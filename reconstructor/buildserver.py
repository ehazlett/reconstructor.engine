#!/usr/bin/env python
import os
import logging
import requests
import time
import sys
import urllib2
import shutil
import tempfile
import tarfile
import pycurl
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
            data = {
                'uuid': self._build_uuid,
                'log': '{0} {1}: {2}'.format(msg.levelname, msg.name, msg.msg),
            }
            r = requests.post(self._build_status_url, data=json.dumps(data), headers=self._headers)
        except Exception, e:
            # ignore errors
            pass

class BuildServer(object):
    def __init__(self, app_url=None, key=None, output_dir=None, apt_cacher_host=None, \
        mirror=None, **kwargs):
        if not app_url or not key:
            raise RuntimeError('You must specify a Reconstructor url and key to use the build server')
        # check url
        if 'http' not in app_url:
            raise RuntimeError('You must specify either http:// or https:// in app_url')
        self._app_url = app_url
        self._apt_cacher_host = apt_cacher_host
        self._key = key
        self._mirror = mirror
        if not output_dir:
            self._output_dir = os.getcwd()
        else:
            self._output_dir = output_dir
        self._headers = {
            'X-BUILDSERVER-VERSION': reconstructor.__version__,
            'X-BUILDSERVER-KEY': self._key,
        }
        self._queue_url = '{0}/api/builds/next'.format(self._app_url)
        self._build_status_url = '{0}/api/builds/update'.format(self._app_url)
        self._build_package_url = '{0}{1}'.format(self._app_url, '/api/builds/{0}/package')
        self._build_upload_url = '{0}/api/builds/upload'.format(self._app_url)
        self._log = logging.getLogger('buildserver')
        self._requests_log = logging.getLogger('requests')
        self._requests_log.setLevel(logging.ERROR)
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
        if self._apt_cacher_host:
            self._log.debug('Using APT cacher at {0}'.format(self._apt_cacher_host))
        self._log.info('Starting Build Server')
        try:
            while True:
                # get next build
                try:
                    r = requests.get(self._queue_url, headers=self._headers)
                except Exception, e:
                    self._log.warn('Unable to check for next build: {0}'.format(e))
                    continue
                if r.status_code == 200:
                    build_data = json.loads(r.content)
                    self._log.debug(build_data)
                    self._build_uuid = build_data['uuid']
                    distro = build_data['distro']
                    self._log.debug('Using {0} for base distro'.format(distro['name']))
                    #r = requests.get('{0}/api/builds/{1}/package'.format(self._app_url, \
                    #    build_data['uuid']), headers=self._headers)
                    # setup custom logger
                    bl = logging.getLogger('build')
                    blh = BuildLogHandler(build_uuid=build_data['uuid'], \
                        build_status_url=self._build_status_url, headers=self._headers)
                    blh.setLevel(logging.DEBUG)
                    bl.addHandler(blh)
                    # get project package for build
                    r = urllib2.urlopen(urllib2.Request(self._build_package_url.format(\
                        build_data['uuid']), headers=self._headers))
                    tmp_prj_file = tempfile.mktemp()
                    with open(tmp_prj_file, 'wb') as f:
                        shutil.copyfileobj(r,f)
                    tmp_dir = tempfile.mkdtemp()
                    tf = tarfile.open(tmp_prj_file, 'r:gz')
                    tf.extractall(tmp_dir)
                    tf.close()
                    # check config
                    cfg_file = os.path.join(tmp_dir, 'project.json')
                    if not os.path.exists(cfg_file):
                        bl.error('Invalid project config')
                        self._update_build_status(status='error', result='Error loading project config')
                        continue
                    # load config
                    try:
                        prj_cfg = json.loads(open(cfg_file, 'r').read())
                    except Exception, e:
                        bl.error('Unable to parse config: {0}'.format(e))
                        self._update_build_status(status='error', result='Error loading project config')
                        continue
                    bl.info('Starting build')
                    self._update_build_status(status='running', result='Starting build')
                    prj = None
                    # load distro type
                    distro = build_data['distro']['name'].lower()
                    if distro == 'debian':
                        cur_dir = os.getcwd()
                        os.chdir(tmp_dir)
                        from reconstructor.distro.debian import Debian
                        prj = Debian(project=tmp_prj_file, apt_cacher_host=self._apt_cacher_host, \
                            mirror=self._mirror, extra_log_handler=blh)
                        self._update_build_status(status='running', result='Building')
                        prj.build()
                        self._update_build_status(status='complete', result='Build complete')
                        prj_iso = '{0}-{1}.iso'.format(prj_cfg['name'], prj_cfg['arch'])
                        tries = 0
                        if os.path.exists(prj_iso):
                            # upload
                            # requests.post causes out of memory errors with large files...
                            #r = requests.post(self._build_upload_url, headers=self._headers, \
                            #    files={'build': ('{0}.iso'.format(build_data['uuid']), \
                            #        open(prj_iso, 'rb'))})
                            while True:
                                try:
                                    r = pycurl.Curl()
                                    r.setopt(pycurl.URL, self._build_upload_url)
                                    for k,v in self._headers.iteritems():
                                        r.setopt(pycurl.HTTPHEADER, ['{0}: {1}'.format(k,v)])
                                    r.setopt(pycurl.HTTPPOST, [('build', (pycurl.FORM_FILE, prj_iso, pycurl.FORM_FILENAME, '{0}.iso'.format(build_data['uuid'])))])
                                    r.perform()
                                except Exception, e:
                                    self._log.warn('Error during upload: {0} ; trying again...'.format(e))
                                    if tries < 3:
                                        tries += 1
                                        time.sleep(10)
                                    else:
                                        bl.error('Unable to upload build.  Please contact support.')
                                        self._update_build_status(status='error', result='Error building project.  Please contact support.')
                                        break
                        else:
                            self._update_build_status(status='error', result='Error building project.  Please contact support.')
                        bl.info('Build complete')
                        os.chdir(cur_dir)
                        os.remove(tmp_prj_file)
                        shutil.rmtree(tmp_dir)
                    else:
                        bl.error('Unknown distro: {0}'.format(distro))
                        self._update_build_status(status='error', result='Unknown distro: {0}'.format(distro))
                        continue
                    # reset build_uuid
                    self._build_uuid = None
                time.sleep(5)
        except KeyboardInterrupt:
            self._log.info('Stopping Build Server')
            sys.exit(0)
