#!/usr/bin/env python
#
# Copyright (C) 2018 Nikhil Dhandre (digitronik).
#
# This file is part of miqbox project. You can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version (GPLv2) of the License.


import os
import socket
import sys
import time
import xml.etree.ElementTree as ET

import click
import libvirt
import requests
from bs4 import BeautifulSoup
from ruamel.yaml import safe_dump, safe_load

from miqbox.ap import ApplianceConsole
from miqbox.miq_xmls import miq_ap, miq_storage_pool, miq_volume

VM_STATE = {
    libvirt.VIR_DOMAIN_RUNNING: "running",
    libvirt.VIR_DOMAIN_BLOCKED: "idle",
    libvirt.VIR_DOMAIN_PAUSED: "paused",
    libvirt.VIR_DOMAIN_SHUTDOWN: "in shutdown",
    libvirt.VIR_DOMAIN_SHUTOFF: "shut off",
    libvirt.VIR_DOMAIN_CRASHED: "crashed",
    libvirt.VIR_DOMAIN_NOSTATE: "no state",
}

home = os.environ["HOME"]


class Connection(object):
    def __init__(self):
        self.conn = None
        self.cfg = None


connection = click.make_pass_decorator(Connection, ensure=True)


@click.version_option()
@click.group()
@connection
def cli(connection):
    """Command line application entry point"""

    conf = Configuration()
    connection.cfg = conf.read()
    url = connection.cfg.get("hypervisor_driver")

    try:
        connection.conn = libvirt.open(url)
    except Exception:
        click.echo("Failed to open connection to {url}".format(url=url))
        exit(1)


class Configuration(object):
    """Configure miqbox"""

    def __init__(self):
        self.conf_file = "{home}/.config/miqbox/conf.yml".format(home=home)
        dir_path = os.path.dirname(self.conf_file)

        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)

        if not os.path.isfile(self.conf_file):
            raw_cfg = {
                "repository": {"upstream": "http://releases.manageiq.org", "downstream": "None"},
                "local_image": "{home}/.miqbox".format(home=home),
                "libvirt_image": "/var/lib/libvirt/images/miqbox",
                "hypervisor_driver": "qemu:///system",
                "storage_pool": "miqbox",
            }
            self.write(raw_cfg)

    def read(self):
        with open(self.conf_file, "r") as ymlfile:
            return safe_load(ymlfile)

    def write(self, cfg):
        if not os.path.isdir(cfg.get("libvirt_image")):
            os.system("sudo mkdir -p {}".format(cfg.get("libvirt_image")))

        if not os.path.isdir(cfg.get("local_image")):
            os.mkdir(cfg.get("local_image"))

        with open(self.conf_file, "w") as ymlfile:
            return safe_dump(cfg, ymlfile, default_flow_style=False)


@connection
def get_appliances(connection, status=None):
    """Get appliances as per current status

    Args:
        status: (`str`) running, shut off, paused, idle, crashed, no state

    Returns:
        (`dirt`) all appliances/ appliances are per status
    """
    domains = {domain.name(): domain for domain in connection.conn.listAllDomains()}

    if status:
        return {name: dom for name, dom in domains.items() if VM_STATE[dom.state()[0]] == status}
    else:
        return domains


def get_hostnames(domain):
    """Get hostname assigned to appliances

    Args:
        domain: libvirt domain object

    Returns:
        (`dirt`) hostnames (vnet, eth, lo)
    """

    ips = dict()
    if domain.isActive():
        try:
            ifaces = domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE, 0)
            for iface, address in ifaces.items():
                ips[iface] = [
                    item["addr"]
                    for item in address["addrs"]
                    if item["type"] == libvirt.VIR_IP_ADDR_TYPE_IPV4
                ]
            return ips
        except Exception:
            return ips
    else:
        return ips


def get_vm_info(domain):
    """Get information of appliances

    Args:
        domain: libvirt domain object

    Returns:
        (`dirt`) having id, name, uuid, state, hostname
    """

    id = domain.ID() if domain.ID() > 0 else "---"
    ips = get_hostnames(domain)
    for conn, ip in ips.items():
        if "lo" == conn:
            pass
        else:
            ip = ip[0]
            break
    else:
        ip = "---"

    return {
        "id": id,
        "name": domain.name(),
        "UUID": domain.UUIDString(),
        "state": VM_STATE[domain.state()[0]],
        "hostname": ip,
    }


@connection
def download_img(connection, url):
    """Download image with click progress bar

    Args:
        url: cloud image url
    """
    img_dir = connection.cfg.get("local_image")
    img_name = url.split("/")[-1]
    click.echo("Download request for: {img_name}".format(img_name=img_name))
    r = requests.get(url, stream=True)

    if r.status_code != requests.codes.ok:
        click.echo("Unable to connect {url}".format(url=url))
        r.raise_for_status()

    total_size = int(r.headers.get("Content-Length"))
    local_img_path = "{dir}/{img}".format(dir=img_dir, img=img_name)

    with click.progressbar(r.iter_content(1024), length=total_size) as bar, open(
        local_img_path, "wb"
    ) as file:
        for chunk in bar:
            file.write(chunk)
            bar.update(len(chunk))


def get_repo_img(url, extension="qcow2", ssl_verify=False):
    """collect available cloud remote images

    Args:
        url: cloud image url
        extension: image extension
        ssl_verify: bool
    """
    try:
        page = requests.get(url, verify=ssl_verify).text
    except (socket.gaierror, requests.exceptions.ConnectionError):
        click.echo("Check Network connection")
        exit(1)
    soup = BeautifulSoup(page, "html.parser")
    return [
        node.get("href") for node in soup.find_all("a") if node.get("href").endswith(extension)
    ]


@connection
def get_storage_pool(connection, name, path, autostart=True, active=True):
    """Get storage pool else create.

    Args:
        name: storage pool name
        path: storage pool path (dir)
        autostart: start pool at boot
        active: active pool

    Return: storage pool
    """
    try:
        pool = connection.conn.storagePoolLookupByName(name)
    except Exception:
        if not os.path.exists(path):
            os.system("sudo mkdir {}".format(path))

        pool_xml = miq_storage_pool.format(name=name, path=path)
        pool = connection.conn.storagePoolDefineXML(pool_xml, 0)
        if not pool:
            click.echo("Failed to create StoragePool object.", file=sys.stderr)
            exit(1)

    if active and not pool.isActive():
        pool.create()

    if autostart and not pool.autostart():
        pool.setAutostart(autostart=True)

    return pool


@connection
def create_disk(connection, name, size, format="qcow2"):
    """Create storage disk

    Args:
        name: disk name
        size: disk size
        format: disk image format

    Return: storage volume
    """
    pool_name = connection.cfg.get("storage_pool")
    pool_path = connection.cfg.get("libvirt_image")
    pool = get_storage_pool(name=pool_name, path=pool_path)

    stgvol_xml = miq_volume.format(name=name, size=size, format=format, path=pool_path)

    try:
        return pool.createXML(stgvol_xml, 0)
    except Exception:
        return False


@connection
def create_appliance(connection, name, base_img, db_img, cpu, memory, version):
    """Create appliance domain

     Args:
         name: appliance name
         base_img: appliance image name
         db_img: database image name
         cpu: cpu count
         memory: appliance memory
         version: appliance version
     Return: libvirt domain
     """
    pool_path = connection.cfg.get("libvirt_image")
    app_xml = miq_ap.format(
        name=name,
        base_img=base_img,
        db_img=db_img,
        cpu=str(cpu),
        memory=str(memory),
        path=pool_path,
        version=version,
    )
    dom = connection.conn.defineXML(app_xml)
    if dom:
        return dom
    else:
        return None


@cli.command(help="Configure miqbox")
def config():
    """Configure Miqbox"""

    conf = Configuration()
    cfg = conf.read()

    cfg["hypervisor_driver"] = click.prompt(
        "Hypervisor drivers url", default=cfg.get("hypervisor_driver")
    )
    cfg["storage_pool"] = click.prompt("Storage Pool Name", default=cfg.get("storage_pool"))
    cfg["libvirt_image"] = click.prompt("Storage Pool Path", default=cfg.get("libvirt_image"))
    cfg["local_image"] = click.prompt("Local Image Location", default=cfg.get("local_image"))
    cfg["repository"]["upstream"] = click.prompt(
        "Upstream Repository", default=cfg["repository"]["upstream"]
    )
    if click.confirm("Do you want to set downstream repository?"):
        cfg["repository"]["downstream"] = click.prompt(
            "Downstream Repository", default=cfg["repository"]["downstream"]
        )

    conf.write(cfg=cfg)
    click.echo("Configuration saved successfully...")


@cli.command(help="Appliance Status")
@click.option("-a", "--all", is_flag=True, help="All Appliances")
@click.option("-r", "--running", is_flag=True, help="All Running Appliances")
@click.option("-s", "--stop", is_flag=True, help="All Stopped Appliances")
def status(all, running, stop):
    """Get appliances status

    Args:
        all: default will return all appliances status
        running: will return all running appliances status
        stop: will return all stop appliances status

    Returns:
        echo status on cli
    """
    if running:
        status = "running"
    elif stop:
        status = "shut off"
    else:
        status = None

    data = [get_vm_info(domain) for domain in get_appliances(status=status).values()]

    for index, info in enumerate(data):
        if not index:
            click.echo("{:<5s}{:<20s}{:^10s}{:^15s}".format("Id", "Name", "Status", "Hostname"))
        click.echo(
            "{:<5s}{:<20s}{:^10s}{:^15s}".format(
                str(info["id"]), info["name"], info["state"], info["hostname"]
            )
        )


@cli.command(help="Start Appliance")
@click.argument("name", type=click.STRING)
@connection
def start(connection, name):
    """ Start/ Invoke appliance

    Args:
        name: (`str`) appliance name
    """

    try:
        domain = connection.conn.lookupByName(name)
    except Exception:
        click.echo("Appliance {name} not found".format(name=name))
        click.echo("Select from appliance: ")
        for app_name in get_appliances(status="shut off").keys():
            click.echo(app_name)
        exit(1)

    try:
        domain.create()
    except Exception:
        click.echo("Fail to start appliance...")


@cli.command(help="Restart Miq/CFME Server")
@click.option("-r", "--restart", nargs=1)
@connection
def evmserver(connection, restart):
    """Restart Miq/CFME server of appliance

    Args:
        restart: (`str` or 'int') appliance name or id
    """
    try:
        id = int(restart)
        dom = connection.conn.lookupByID(id)
    except ValueError:
        dom = connection.conn.lookupByName(restart)

    raw_xml = dom.XMLDesc(0)
    root = ET.fromstring(raw_xml)
    version = (root.findall("description")[0]).text
    hostname = get_vm_info(dom).get("hostname", None)
    ap = ApplianceConsole(hostname=hostname, user="root", password="smartvm", version=version)
    if ap.connect():
        ap.server_restart()
        click.echo("Miq/CFME appliance server restarted successfully...")


@cli.command(help="Stop Appliance")
@click.argument("name")
@connection
def stop(connection, name):
    """Stop running appliance

    Args:
        name: (`str`) appliance name
    """

    try:
        id = int(name)
        dom = connection.conn.lookupByID(id)
    except ValueError:
        dom = connection.conn.lookupByName(name)

    if dom:
        if dom.isActive():
            dom.shutdown()
    else:
        click.echo("Select from running appliance:")
        for name, dom in get_appliances("running"):
            click.echo("{id} ==> {name}".format(id=str(dom.ID()), name=name))


@cli.command(help="Kill Appliance")
@click.argument("name")
@connection
def kill(connection, name):
    """Kill appliance

    Args:
        name: (`str`) appliance name
    """

    try:
        try:
            id = int(name)
            dom = connection.conn.lookupByID(id)
        except ValueError:
            dom = connection.conn.lookupByName(name)
    except Exception:
        exit(1)

    if dom:
        if dom.isActive() > 0:
            dom.shutdown()
            timeout = time.time() + 180
            while True:
                if dom.isActive() == 0:
                    break
                if time.time() > timeout:
                    click.echo("Fail to shutdown appliance")
                    exit(1)

        storage = connection.cfg.get("storage_pool")
        try:
            pool = connection.conn.storagePoolLookupByName(storage)
        except Exception:
            click.echo(
                "{storage} storage pool not found need to configure proper pool name".format(
                    storage
                )
            )
            exit(1)

        storage_db = {item.name(): item for item in pool.listAllVolumes()}
        raw_xml = dom.XMLDesc(0)
        root = ET.fromstring(raw_xml)
        disks = root.findall("devices/disk")
        for disk in disks:
            source = disk.find("source").get("file")
            file = os.path.basename(source)
            storage = storage_db.get(file, None)
            if storage:
                storage.delete()
            if os.path.isfile(source):
                os.system("sudo rm -rf {f}".format(f=source))
                click.echo("Disk '{source} removed'...".format(source=file))
        dom.undefine()
    else:
        click.echo("Please select proper Name or Id of appliance")


@cli.command()
@click.option("-l", "--local", is_flag=True, help="All available local images")
@click.option("-r", "--remote", is_flag=True, help="All available remote images")
@click.option("-f", "--filter", type=str, help="Filter specific image")
@connection
def images(connection, local, remote, filter):
    """Get local or remote available image

    Args:
        local: default, will give local images
        remote: will return remote repository available images
    """

    img_dir = connection.cfg.get("local_image")
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    if remote:
        stream = click.prompt(
            "stream:", default="downstream", type=click.Choice(["downstream", "upstream"])
        )
        base_repo = connection.cfg["repository"].get(stream)
        if stream == "downstream":
            ver = click.prompt(
                "Version:", default="5.11", type=click.Choice(["5.8", "5.9", "5.10", "5.11"])
            )
            extension = "qcow2"
        else:
            ver = "manageiq"
            extension = "qc2"

        if stream == "upstream":
            url = base_repo
        else:
            url = "{base_repo}/builds/cfme/{ver}/stable".format(base_repo=base_repo, ver=ver)

        for img in get_repo_img(url=url, extension=extension):
            if filter:
                click.echo(img) if filter in img else 0
            else:
                click.echo(img)
    else:
        for img in os.listdir(img_dir):
            if filter:
                click.echo(img) if filter in img else 0
            else:
                click.echo(img)


@cli.command(help="Download Image")
@click.argument("image_name")
@connection
def pull(connection, image_name):
    """Pull image available on remote repository
    Note: Image name can found by images -r command

    Args:
        image_name: (`str`) image name
    """

    if "manageiq" in image_name:
        stream = ver = "upstream"
    else:
        stream = "downstream"

        for _ver in ["5.11", "5.10", "5.9", "5.8"]:
            if _ver in image_name:
                ver = _ver
                break
        else:
            raise NameError("Downstream version not matched with image name")

    base_repo = connection.cfg["repository"].get(stream)
    if stream == "upstream":
        url = "{base_repo}/{name}".format(base_repo=base_repo, name=image_name)
    else:
        url = "{base_repo}/builds/cfme/{ver}/stable/{name}".format(
            base_repo=base_repo, ver=ver, name=image_name
        )

    if url:
        img_dir = connection.cfg.get("local_image")
        if image_name not in os.listdir(img_dir):
            download_img(url=url)
        else:
            click.echo("{img} already available".format(img=image_name))


@cli.command(help="Remove local Images")
@click.argument("image_names", nargs=-1)
@connection
def rmi(connection, image_names):
    """Remove local images

    Args:
        image_names: list of local image names
    """
    img_dir = connection.cfg.get("local_image")
    for image in image_names:
        if image in os.listdir(img_dir):
            os.system("rm -rf '{img_dir}/{name}'".format(img_dir=img_dir, name=image))
        else:
            click.echo("{img} not available".format(img=image))


@cli.command(help="Create Appliance")
@click.option("--name", prompt="Appliance name")
@click.option("--image", prompt="Image name")
@click.option("--cpu", default=1, prompt="CPU count")
@click.option("--memory", default=4, prompt="Memory in GiB")
@click.option("--db_size", default=5, prompt="Database size in GiB")
@connection
def create(connection, name, image, cpu, memory, db_size, db=None):
    """Create appliance

    Args:
        name: Name of appliance
        image: Base image for appliance creation
        memory: Memory allocated to appliance
        db_size: Database size
    """
    image_dir = connection.cfg.get("local_image")
    libvirt_dir = connection.cfg.get("libvirt_image")
    db_disk_name = "{app_name}-db".format(app_name=name)
    extension = image.split(".")[-1]
    base_disk_name = "{name}.{ext}".format(name=name, ext=extension)
    stream = image.split("-")[2]

    if image in os.listdir(image_dir):
        source = os.path.join(image_dir, image)
        destination = os.path.join(libvirt_dir, base_disk_name)
        os.system("sudo cp {source} {destination}".format(source=source, destination=destination))
        click.echo("Base appliance disk created...")
    else:
        click.echo("Image '{img}' not available...".format(img=image))
        exit(0)

    try:
        db = create_disk(name=db_disk_name, size=db_size, format=extension)
        click.echo("Database disk created...")
    except Exception:
        click.echo("Database disk creation fails...")
        os.system("sudo rm -rf {dest}".format(dest=destination))
        exit(0)

    if db:
        dom = create_appliance(
            name=name,
            base_img=base_disk_name,
            db_img=db.name(),
            cpu=cpu,
            memory=memory,
            version=stream,
        )
        if dom:
            dom.create()
            click.echo("Appliance {name} created successfully...".format(name=dom.name()))
        else:
            click.echo("Fails to create {name} appliance...".format(name=dom.name()))
            exit(0)

    if not stream.isalpha():
        # pre-database configuration only need for downstream
        conf = click.prompt(
            "Do you want to setup internal database?", default="y", type=click.Choice(["y", "n"])
        )

        if conf == "y":
            click.echo("wait... it will take some time to configure db...")
            start_time = time.time()
            while time.time() < start_time + 30:
                hostname = get_vm_info(dom).get("hostname", None)
                if hostname.count(".") == 3:
                    break
            else:
                click.echo("Unable to get hostname for appliance... try latter")
                exit(0)

            ap = ApplianceConsole(
                hostname=hostname, user="root", password="smartvm", version=stream
            )
            if ap.connect():
                ap.db_config()
                click.echo("Appliance database configured successfully...")
