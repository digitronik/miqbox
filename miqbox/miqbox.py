#!/usr/bin/env python
#
# Copyright (C) 2018 Nikhil Dhandre (digitronik).
#
# This file is part of miqbox project. You can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version (GPLv2) of the License.
import os
import time
import xml.etree.ElementTree as ET
from distutils.version import LooseVersion
from shutil import copyfile
from shutil import get_terminal_size

import click
import libvirt

from miqbox.client import Client
from miqbox.console import Console
from miqbox.miq_xmls import APPLIANCE
from miqbox.miq_xmls import POOL
from miqbox.miq_xmls import VOLUME

APP_STATES = {
    libvirt.VIR_DOMAIN_RUNNING: "running",
    libvirt.VIR_DOMAIN_BLOCKED: "idle",
    libvirt.VIR_DOMAIN_PAUSED: "paused",
    libvirt.VIR_DOMAIN_SHUTDOWN: "in shutdown",
    libvirt.VIR_DOMAIN_SHUTOFF: "shut off",
    libvirt.VIR_DOMAIN_CRASHED: "crashed",
    libvirt.VIR_DOMAIN_NOSTATE: "no state",
}


class MiqBox(Client):
    def appliances(self, by_id=False, status=None):
        """Get appliances as per current status

        Args:
            by_id (bool): appliance with id
            status (str): running, shut off, paused, idle, crashed, no state

        Returns:
            (dirt) all appliances/ appliances are per status
        """
        if by_id:
            apps = {
                domain.ID(): Appliance(domain.name()) for domain in self.driver.listAllDomains()
            }
        else:
            apps = {
                domain.name(): Appliance(domain.name()) for domain in self.driver.listAllDomains()
            }

        if status:
            return {name: app for name, app in apps.items() if APP_STATES[app.state] == status}
        else:
            return apps

    def get_appliance(self, name, status=None):
        """Get appliance

        Args:
            name (str): name of appliance
            status (str): running, shut off, paused, idle, crashed, no state
        """
        try:
            id = int(name)
            domain = self.appliances(by_id=True, status=status).get(id)
        except ValueError:
            domain = self.appliances(status=status).get(name)
        return domain if domain else None

    @property
    def pool(self):
        """Get storage pool"""
        try:
            return self.driver.storagePoolLookupByName(self.libvirt.pool_name)
        except libvirt.libvirtError:
            return None

    def create_pool(self, active=True, autostart=True):
        """Create storage pool

        Args:
            active (bool): pool status
            autostart (bool); pool start at boot

        Returns:
            libvirt pool
        """
        pool_xml = POOL.format(name=self.libvirt.pool_name, path=self.libvirt.pool_path)
        pool = self.driver.storagePoolDefineXML(pool_xml, 0)

        if active and not pool.isActive():
            pool.create()

        if autostart and not pool.autostart():
            pool.setAutostart(autostart=True)

        return pool

    def create_disk(self, name, size, format="qcow2"):
        """Create storage disk

        Args:
            name (str): disk name
            size (int): disk size
            format (str): disk image format for upstream qc2 and qcow2 for downstream.

        Returns:
            libvirt volume
        """
        stgvol_xml = VOLUME.format(name=name, size=size, format=format, path=self.libvirt.pool_path)
        pool = self.pool if self.pool else self.create_pool()

        try:
            return pool.createXML(stgvol_xml, 0)
        except libvirt.libvirtError:
            return None

    def create_appliance(self, name, base_img, db_img, cpu, memory, stream, provider, version):
        """Create appliance domain

        Args:
            name (str): name of appliance
            base_img (str): image name (appliance)
            db_img (str): image name (database)
            cpu (int): cpu count
            memory (int): memory in GB
            stream (str): appliance stream (cfme/manageiq)
            provider (str): appliance provider (rhv/osp/etc...)
            version (str): appliance version

        Return: libvirt domain
        """
        app_xml = APPLIANCE.format(
            name=name,
            base_img=base_img,
            db_img=db_img,
            cpu=str(cpu),
            memory=str(memory),
            path=self.libvirt.pool_path,
            stream=stream,
            provider=provider,
            version=version,
        )
        try:
            dom = self.driver.defineXML(app_xml)
            dom.create()
            return Appliance(name=name)
        except libvirt.libvirtError:
            return None


class Appliance(Client):
    """MiqBox appliance

    Args:
        name (str): name of appliance
        id (int): id of appliance
        credentials (nametuple): appliance credentials (username, password)
    """

    def __init__(self, name=None, id=None, credentials=None, *args, **kwargs):
        super(Appliance, self).__init__(*args, **kwargs)
        self.name = name
        self.id = id
        self.creds = credentials or self.credentials

        if not (name or id):
            raise AttributeError("Need id or name")

    @property
    def app(self):
        if self.id:
            return self.driver.lookupByID(self.id)
        else:
            return self.driver.lookupByName(self.name)

    @property
    def xml_data(self):
        return ET.fromstring(self.app.XMLDesc(0))

    @property
    def is_active(self):
        """check appliance is active"""
        return bool(self.app.isActive())

    @property
    def state(self):
        """get appliance state"""
        return self.app.state()[0]

    @property
    def pool(self):
        """get storage pool"""
        try:
            return self.driver.storagePoolLookupByName(self.libvirt.pool_name)
        except libvirt.libvirtError:
            return None

    def start(self):
        """start appliance"""
        if self.is_active:
            return False
        else:
            self.app.create()
            return True

    def stop(self):
        """stop appliance"""
        if self.is_active:
            self.app.shutdown()
            return True
        else:
            return False

    def kill(self):
        """remove appliance"""
        if self.is_active:
            self.stop()
            timeout = time.time() + 120

            while True:
                if not self.is_active:
                    break
                if time.time() > timeout:
                    print("Fail to shutdown appliance")
                    return False

        storage_db = {item.name(): item for item in self.pool.listAllVolumes()}
        disks = self.xml_data.findall("devices/disk")

        for disk in disks:
            source = disk.find("source").get("file")
            file = os.path.basename(source)
            storage = storage_db.get(file)

            if storage:
                storage.delete()

            if os.path.isfile(source):
                os.remove(source)

            print(f"Disk '{file} removed'...")

        # undefine appliance to remove
        self.app.undefine()
        return True

    @property
    def hostname(self):
        """Get hostname assigned to appliances"""

        ips = dict()
        if self.app.isActive():
            ifaces = self.app.interfaceAddresses(
                libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE, 0
            )
            for iface, address in ifaces.items():
                ips[iface] = [
                    item["addr"]
                    for item in address["addrs"]
                    if item["type"] == libvirt.VIR_IP_ADDR_TYPE_IPV4
                ]

        ips = [ips[0] for conn, ips in ips.items() if conn != "lo"]
        return ips[0] if ips else "---"

    @property
    def stream(self):
        """get appliance stream"""
        return self.xml_data.find("description").text.split("-")[0]

    @property
    def provider(self):
        """get appliance provider"""
        return self.xml_data.find("description").text.split("-")[1]

    @property
    def version(self):
        """get appliance version"""
        return LooseVersion(self.xml_data.find("description").text.split("-")[2])

    def info(self):
        """Get information of appliances

        Returns:
            dirt: having id, name, state, hostname
        """
        return {
            "id": self.app.ID() if self.app.ID() > 0 else "---",
            "name": self.app.name(),
            "state": APP_STATES[self.app.state()[0]],
            "hostname": self.hostname,
        }


@click.command(help="Appliance Status")
@click.option("-a", "--all", is_flag=True, help="All Appliances")
@click.option("-r", "--running", is_flag=True, help="All Running Appliances")
@click.option("-s", "--stop", is_flag=True, help="All Stopped Appliances")
def status(all, running, stop):
    """Get appliances status"""

    if running:
        status = "running"
    elif stop:
        status = "shut off"
    else:
        status = None

    box = MiqBox()
    data = [Appliance(name=name).info() for name in box.appliances(status=status)]
    entities = "{:<5s}{:<28s}{:^15s}{:^15s}"
    for index, info in enumerate(data):
        if not index:
            click.echo(entities.format("Id", "Name", "Status", "Hostname"))
        click.echo(entities.format(str(info["id"]), info["name"], info["state"], info["hostname"]))


@click.command(help="Start Appliance")
@click.argument("name", type=click.STRING)
def start(name):
    """ Start/ Invoke appliance"""

    box = MiqBox()
    app = box.get_appliance(name, status="shut off")

    if app:
        app.start()
    else:
        click.echo(f"Appliance {name} not found")
        click.echo("Select from appliance: ")
        for app_name in box.appliances(status="shut off"):
            click.echo(app_name)


@click.command(help="Restart Miq/CFME Server")
@click.option("-r", "--restart", nargs=1)
def evmserver(restart):
    """Restart Miq/CFME server of appliance"""

    box = MiqBox()
    app = box.get_appliance(restart, status="running")
    app_console = Console(appliance=app)
    app_console.restart_server()
    click.echo(f"{app.app.name()} server restarted successfully...")


@click.command(help="Stop Appliance")
@click.argument("name")
def stop(name):
    """Stop running appliance"""

    box = MiqBox()
    app = box.get_appliance(name, status="running")

    if app:
        app.stop()
    else:
        click.echo("Select from running appliance:")
        for app_name in box.appliances(status="running"):
            click.echo(app_name)


@click.command(help="Kill Appliance")
@click.argument("name")
def kill(name):
    """Kill appliance"""
    box = MiqBox()
    app = box.get_appliance(name)

    if app:
        app.kill()
    else:
        click.echo("Please select proper Name or Id of appliance")


@click.command(help="Create Appliance")
@click.option("--image", prompt="Image name")
@click.option("--cpu", default=1, prompt="CPU count")
@click.option("--memory", default=4, prompt="Memory in GiB")
@click.option("--db_size", default=5, prompt="Database size in GiB")
@click.option("--count", default=1, prompt="Number of appliance")
def create(image, cpu, memory, db_size, count, configure=False):
    """Create appliance"""
    _apps = {}
    box = MiqBox()
    stream, prov, version, *_ = image.split("-")
    extension = image.split(".")[-1]

    name = click.prompt("Appliance Name:", default=f"{stream}-{version}")
    if stream != "manageiq":
        # pre-database configuration only need for downstream
        configure = click.confirm("Do you want to setup internal database?")

    for _ in range(count):
        app_name = f"{name}-{time.strftime('%y%m%d-%H%M%S')}"
        db_disk_name = f"{app_name}-db"
        base_disk_name = f"{app_name}.{extension}"

        if image in os.listdir(box.image_path):
            source = os.path.join(box.image_path, image)
            destination = os.path.join(box.libvirt.pool_path, base_disk_name)
            copyfile(source, destination)
            click.echo("Base appliance disk created...")
        else:
            click.echo("Image '{img}' not available...".format(img=image))
            exit(0)

        db = box.create_disk(name=db_disk_name, size=db_size, format=extension)

        if db:
            click.echo("Database disk created...")
        else:
            click.echo("Database disk creation fails...")
            os.remove(destination)
            exit(1)

        app = box.create_appliance(
            name=app_name,
            base_img=base_disk_name,
            db_img=db.name(),
            cpu=cpu,
            memory=memory,
            stream=stream,
            provider=prov,
            version=version,
        )
        if app:
            click.echo(f"Appliance {app_name} created successfully...")

            click.echo("Waiting for hostname...")
            start_time = time.time()

            while time.time() < start_time + 90:
                if app.hostname.count(".") == 3:
                    break
            else:
                click.echo("Unable to get hostname for appliance...")
                exit(0)
            # save hostname
            _apps[app_name] = app.hostname
        else:
            click.echo(f"Fails to create {app_name} appliance...")
            exit(1)

        if configure:
            click.echo("Database configuration will take some time...")
            click.echo(f"Appliance hostname: {app.hostname}")
            app_console = Console(appliance=app)
            app_console.config_database()
            click.echo(f"{app.name} database configured successfully...")

    if _apps:
        columns = get_terminal_size().columns
        click.echo("=" * columns)
        click.echo("Applications created successfully".center(columns))
        for name, hostname in _apps.items():
            click.echo(click.style(f"{name}: {hostname}".center(columns), bold=True))
        click.echo(
            click.style(
                "Note: If Web-UI not respond; Check EVM Server process".center(columns), bold=True,
            )
        )
        click.echo("=" * columns)
