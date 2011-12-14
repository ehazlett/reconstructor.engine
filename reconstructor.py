#!/usr/bin/env python
from argparse import ArgumentParser
from reconstructor.distro.debian import Debian
import sys
import logging

APP_NAME = 'Reconstructor'
APP_VERSION = '4.0'
LOG_LEVEL = logging.DEBUG

logging.basicConfig(level=LOG_LEVEL, \
    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

if __name__=='__main__':
    available_distros = ['debian']
    parser = ArgumentParser(\
        description='{0}\n\nGNU/Linux distribution creator'.format(APP_NAME))
    parser.add_argument("--project", action="store", \
        dest="project", default=None, help="Reconstructor project file")
    parser.add_argument("--name", action="store", \
        dest="name", default="DebianCustom", help="Name of project")
    parser.add_argument("--distro", action="store", dest="distro", \
        help="Distro to build (debian, etc.)")
    parser.add_argument("--arch", action="store", dest="arch", \
        default='i386', help="Architecture (i386 or amd64)")
    parser.add_argument("--version", action="store", \
        dest="version", default='squeeze', help="Version to build (squeeze, wheezy, etc.)")
    parser.add_argument("--packages", action="store", \
        dest="packages", default="", help="Additional packages to add")
    parser.add_argument("--apt-cacher-host", action="store", \
        dest="apt_cacher_host", default=None, help="APT cacher host")
    parser.add_argument("--mirror", action="store", \
        dest="mirror", default=None, help="Mirror to use (default: ftp.us.debian.org/debian)")

    args = parser.parse_args()
    prj = None
    if args.project:
        prj = Debian(project=args.project, apt_cacher_host=args.apt_cacher_host, mirror=args.mirror)
    elif args.distro:
        distro = args.distro.lower()
        if distro not in available_distros:
            logging.error('Unknown distro.  Available distros: {0}'.format(\
                ','.join(available_distros)))
            sys.exit(1)
        if distro == 'debian':
            if args.packages.find(',') > -1:
                pkgs = args.packages.split(',')
            else:
                pkgs = [args.packages]
            prj = Debian(arch=args.arch, version=args.version, packages=pkgs, \
                name=args.name, apt_cacher_host=args.apt_cacher_host, mirror=args.mirror)
            
    else:
        parser.print_help()
        logging.error('You must specify a project or distro')
        logging.error('Available distros: {0}'.format(','.join(available_distros)))
        sys.exit(1)
    # build
    if prj:
        prj.build()
        prj.cleanup()
        sys.exit(0)
    parser.print_help()
    sys.exit(0)
    
