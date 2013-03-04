# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant::Config.run do |config|
  config.vm.box = "precise64"
  config.vm.box_url = "http://files.vagrantup.com/precise64.box"
  config.ssh.forward_agent = true
  config.vm.customize ["modifyvm", :id, "--memory", 1024, "--cpus", "2"]
  config.vm.host_name = "reconstructor"
  config.vm.provision :shell, :path => "provision.sh"
end
