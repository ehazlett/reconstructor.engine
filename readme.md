# Reconstructor Engine
GNU/Linux Distribution Toolkit

# Quickstart
Currently there is no PyPI package available as it is still in development.  Here
are instructions on using local.

## Show Help
`sudo python ./reconstructor/runner.py -h`

## Create Minimal Live ISO
`sudo python ./reconstructor/runner.py --name mydist --arch amd64 --codename precise --output-file ~/mydist.iso`

## Create Minimal Live ISO with additional packages
`sudo python ./reconstructor/runner.py --name mydist --arch amd64 --codename precise --output-file ~/mydist.iso --packages="tmux,vim,git-core"`

# Vagrant
You can use the included `Vagrantfile` to get a working build environment.  You
can run `vagrant up ; vagrant ssh`, then `cd /vagrant`.  You can then use the
examples above to build.

