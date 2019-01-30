<a href="https://github.com/digitronik/miqbox/blob/master/LICENSE"><img alt="License: GPL v2" src="https://img.shields.io/badge/License-GPL%20v2-blue.svg"></a>
<a href="https://github.com/ambv/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>

# miqbox
Spin `ManageIQ/CFME` Appliance locally with `Virtualization`.

**Under progress...**


## Prerequisite:

1. Virtualization:

      - [Fedora](https://docs.fedoraproject.org/en-US/quick-docs/getting-started-with-virtualization/)
        ```bash
        sudo dnf install @virtualization
        systemctl start libvirtd
        systemctl enable libvirtd
        ```
        If you want optional packages
        ```bash
        dnf group install --with-optional virtualization
        ```
      - [Ubuntu](https://help.ubuntu.com/community/KVM/Installation)
        ```bash
        sudo apt-get install qemu-kvm
        ```

2. Devel Packages:

    ```bash
    sudo dnf install libvirt-devel python-devel python3-devel
    ```

## Install:
- pip
    ```bash
    pip install miqbox --user
    ```

- source
    ```bash
    python setup.py install --user
    ```
Note: For Development install in editable mode.

## Troubleshooting:
- [libvirt: Polkit error](https://fedoraproject.org/wiki/QA:Testcase_Virt_ACLs)
- To prevent libvirt from asking root password, follow these steps:
    - `groupadd libvirt` (it may be present by default)
    - `sudo usermod -a -G libvirt username`
    - Create a new file for rules:
        - `vim /etc/polkit-1/rules.d/80-libvirt.rules`
        ```
        polkit.addRule(function(action, subject) {
        if (action.id == "org.libvirt.unix.manage"
            && subject.local
            && subject.active
            && subject.isInGroup("libvirt")) {
        return polkit.Result.YES;
        }
        });
        ```


## Usage:
