<a href="https://github.com/digitronik/miqbox/blob/master/LICENSE"><img alt="License: GPL v2" src="https://img.shields.io/badge/License-GPL%20v2-blue.svg"></a>
<a href="https://github.com/ambv/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>

# miqbox
Spin ManageIQ/CFME Appliance locally

**Under progress...**


# Dependencies
You shall need virtualization setup on your system.

## [Fedora](https://docs.fedoraproject.org/en-US/quick-docs/getting-started-with-virtualization/)
```shell
dnf install @virtualization
systemctl start libvirtd
systemctl enable libvirtd
```

## [Ubuntu](https://help.ubuntu.com/community/KVM/Installation)
```shell
sudo apt-get install qemu-kvm
```

# Install
- pip
```shell
pip install --user miqbox
```

- source
```shell
python setup.py install
```

- For Development
Install in editable mode


# Usage
