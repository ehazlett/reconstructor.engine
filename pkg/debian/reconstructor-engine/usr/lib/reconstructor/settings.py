#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
#    settings.py   
#        Settings module
#    Copyright (c) <2009> Reconstructor Team <reconstructor@aperantis.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from datetime import date
import logging

# app vars
LOG_LEVEL=logging.DEBUG
APP_NAME="Reconstructor Engine"
APP_AUTHOR="Lumentica"
APP_VERSION='3.2'
APP_DEV_REV='091223'
APP_CODENAME=''
APP_COPYRIGHT="%s %s (c) %s, %s" % (APP_NAME, str(APP_VERSION), APP_AUTHOR, str(date.today().year))
APP_URL='https://build.reconstructor.org'
SITE_URL='http://www.reconstructor.org'
HELP_URL=SITE_URL + '/wiki/reconstructor/EngineUserGuide'
LVM_ROOT=''
ONLINE_ISO_REPO=''
QUEUE_URL=''
QUEUE_CHECK_INTERVAL = 10 # seconds
MINIMUM_BUILD_FREE_SPACE = 2.0 # minimum space needed for online build (in GB)
REPO_DOWNLOAD_URL='' # TODO: remove -- not used anymore
SCRIPT_TIMEOUT = 600 # timeout for post script (in seconds)
APT_CACHER_ADDRESS = '' # use apt-cacher for package installation (i.e. 127.0.0.1:3142/
MKSQUASHFS_3_3 = '/usr/local/bin/mksquashfs3.3'
UNSQUASHFS_3_3 = '/usr/local/bin/unsquashfs3.3'
MKSQUASHFS_4_0 = '/usr/local/bin/mksquashfs4.0'
UNSQUASHFS_4_0 = '/usr/local/bin/unsquashfs4.0'


