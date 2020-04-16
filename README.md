<h1 align="center"> MiqBox </h1>
<h2 align="center"> Spin ManageIQ/CFME Appliance locally with Virtualization. </h2>

<p align="center">
    <a href="https://pypi.org/project/miqbox"><img alt="Python Versions" src="https://img.shields.io/pypi/pyversions/miqbox.svg?style=flat"></a>
    <a href="https://github.com/digitronik/miqbox/actions"><img alt="Build Status" src="https://github.com/digitronik/miqbox/workflows/Tests/badge.svg?branch=gh_action"></a>
    <a href="https://github.com/digitronik/miqbox/blob/master/LICENSE"><img alt="License: GPLV2" src="https://img.shields.io/pypi/l/miqbox.svg?version=latest"></a>
    <a href="https://pypi.org/project/miqbox/#history"><img alt="PyPI version" src="https://badge.fury.io/py/miqbox.svg"></a>
    <a href="https://pepy.tech/project/miqbox"><img alt="Downloads" src="https://pepy.tech/badge/miqbox"></a>
    <a href="https://pypi.org/project/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

### Prerequisite

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

### Install

- pip

    ```bash
    pip install miqbox --user
    ```

- source

    ```bash
    python setup.py install --user
    ```

### Troubleshooting

- [libvirt: Polkit error](https://fedoraproject.org/wiki/QA:Testcase_Virt_ACLs)

- To prevent `libvirt` from asking `root` password:

    - Add `libvirt` group (It may be present by default)

        ```bash
        sudo groupadd libvirt
        ```

    - Add not root `user` as member

        ```bash
        sudo usermod -a -G libvirt <username>
        ```

    - Add `Polkit` rule for `libvirt`:

        ```bash
        vim /etc/polkit-1/rules.d/80-libvirt.rules
        ```

        ```bash
        polkit.addRule(function(action, subject) {
        if (action.id == "org.libvirt.unix.manage"
            && subject.local
            && subject.active
            && subject.isInGroup("libvirt")) {
        return polkit.Result.YES;
        }
        });
        ```

### Usage

- Help available with `MiqBox`

   ```bash
    Usage: miqbox [OPTIONS] COMMAND [ARGS]...

      Spin ManageIQ/CFME Appliance locally with Virtualization.

    Options:
      --version  Show the version and exit.
      --help     Show this message and exit.

    Commands:
      config     Configure MiqBox
      create     Create Appliance
      evmserver  Restart Miq/CFME Server
      images     Check available images
      kill       Kill Appliance
      pull       Download Image
      rmi        Remove local Images
      start      Start Appliance
      status     Appliance Status
      stop       Stop Appliance

   ```

### Contribute

- Fork the [repository](https://github.com/digitronik/miqbox.git) on GitHub
and make some changes. Make sure to add yourself to [AUTHORS](AUTHORS.md).

- Install the in development mode

    ```bash
    pip install -r requirements-dev.txt
    pip install -e .
    ```

- Send pull requests and bugs.
