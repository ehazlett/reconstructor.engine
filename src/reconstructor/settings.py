#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
#    settings.py   
#        Settings module
#
#    Copyright (C) 2011  Lumentica
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


from datetime import date
import logging
import commands

# app vars
#LOG_LEVEL=logging.INFO
LOG_LEVEL=logging.DEBUG
APP_NAME="Reconstructor Engine"
APP_AUTHOR="Lumentica"
APP_VERSION='3.5'
APP_DEV_REV='20110315'
APP_CODENAME=''
APP_COPYRIGHT="%s %s (c) %s, %s" % (APP_NAME, str(APP_VERSION), APP_AUTHOR, str(date.today().year))
APP_URL='https://reconstructor.apphosted.com'
SITE_URL='http://www.reconstructor.org'
HELP_URL='https://projects.lumentica.com/projects/reconstructor/wiki/EngineUserGuide'
ISO_REPO='/srv/iso_repo'
#LVM_ROOT='/dev/rec'
LVM_ROOT=''
ONLINE_ISO_REPO='/srv/rec_images'
QUEUE_URL='https://reconstructor.apphosted.com/queue/next/'
QUEUE_CHECK_INTERVAL = 10 # seconds
MINIMUM_BUILD_FREE_SPACE = 2.0 # minimum space needed for online build (in GB)
REPO_DOWNLOAD_URL='' # TODO: remove -- not used anymore
SCRIPT_TIMEOUT = 900 # timeout for post script (in seconds)
APT_CACHER_ADDRESS = '' # use apt-cacher for package installation (i.e. 127.0.0.1:3142/
MKSQUASHFS_3_3 = commands.getoutput('which mksquashfs')
UNSQUASHFS_3_3 = commands.getoutput('which unsquashfs')
MKSQUASHFS_4_0 = commands.getoutput('which mksquashfs')
UNSQUASHFS_4_0 = commands.getoutput('which unsquashfs')


