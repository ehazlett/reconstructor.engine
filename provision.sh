#!/bin/sh

# update apt
apt-get -y update 2>&1 > /dev/null
apt-get -y install vim screen python-setuptools python-dev
easy_install pip > /dev/null 2>&1

echo "Configuring Puppet master"
DEBIAN_FRONTEND=noninteractive apt-get install -y build-essential squashfs-tools debootstrap genisoimage syslinux squid-deb-proxy squid-deb-proxy-client

exit 0
