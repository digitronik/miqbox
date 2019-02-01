[![alt text](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](https://github.com/digitronik/miqbox/blob/master/LICENSE)
[![alt text](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)


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
- To prevent `libvirt` from asking `root` password:
    - Add `libvirt` group (It may be present by default)
        ```
        sudo groupadd libvirt
        ``` 
    - Add not root `user` as member
        ```
        sudo usermod -a -G libvirt <username>
        ```
    - Add `Polkit` rule for `libvirt`:
        ```
        vim /etc/polkit-1/rules.d/80-libvirt.rules
        ```
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
   ```
    Usage: miqbox [OPTIONS] COMMAND [ARGS]...
    
      Command line application entry point
    
    Options:
      --help  Show this message and exit.
    
    Commands:
      config     Configure miqbox
      create     Create Appliance
      evmserver  Restart Miq/CFME Server
      images     Get local or remote available image Args: local: default, will...
      kill       Kill Appliance
      pull       Download Image
      rmi        Remove local Image
      start      Start Appliance
      status     Appliance Status
      stop       Stop Appliance
   ```
