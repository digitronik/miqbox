import os
import sys
import time
import xml.etree.ElementTree as ET

import click
import libvirt
import requests
from bs4 import BeautifulSoup


VM_STATE = {
    libvirt.VIR_DOMAIN_RUNNING: "running",
    libvirt.VIR_DOMAIN_BLOCKED: "idle",
    libvirt.VIR_DOMAIN_PAUSED: "paused",
    libvirt.VIR_DOMAIN_SHUTDOWN: "in shutdown",
    libvirt.VIR_DOMAIN_SHUTOFF: "shut off",
    libvirt.VIR_DOMAIN_CRASHED: "crashed",
    libvirt.VIR_DOMAIN_NOSTATE: "no state",
}


class Connection(object):
    def __init__(self):
        self.conn = None
        self.pool = None


pass_connection = click.make_pass_decorator(Connection, ensure=True)


@click.group()
@click.option("--url", default="qemu:///system")
@pass_connection
def cli(connection, url):
    try:
        connection.conn = libvirt.open(url)
    except Exception:
        click.echo("Failed to open connection to {}".format(url), file=sys.stderr)
        exit(1)
    try:
        connection.pool = connection.conn.storagePoolLookupByName("default")
    except Exception:
        click.echo("Failed to open storage pool...")


def get_repo_img(url, extension="qcow2"):
    page = requests.get(url).text
    soup = BeautifulSoup(page, "html.parser")
    return [
        node.get("href") for node in soup.find_all("a") if node.get("href").endswith(extension)
    ]


def download_img(url):
    if not os.path.exists(IMG_DIR):
        os.makedirs(IMG_DIR)

    img_name = url.split("/")[-1]
    click.echo("Download request for: {img_name}".format(img_name=img_name))
    r = requests.get(url, stream=True)

    if r.status_code != requests.codes.ok:
        click.echo("Unable to connect {url}".format(url=url))
        r.raise_for_status()

    total_size = int(r.headers.get("Content-Length"))
    local_img_path = "{dir}/{img}".format(dir=IMG_DIR, img=img_name)
    with click.progressbar(r.iter_content(1024), length=total_size) as bar, open(
        local_img_path, "wb"
    ) as file:
        for chunk in bar:
            file.write(chunk)
            bar.update(len(chunk))


def hostname(domain):
    # IP Address
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


def _vm_info(domain):
    id = domain.ID() if domain.ID() > 0 else "---"

    ips = hostname(domain)
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


@pass_connection
def _vm_not_running(connection):
    return [
        domain.name()
        for domain in connection.conn.listAllDomains()
        if domain.state()[0] != libvirt.VIR_DOMAIN_RUNNING
    ]


@pass_connection
def _vm_running(connection):
    return {
        domain.ID(): domain.name()
        for domain in connection.conn.listAllDomains()
        if domain.state()[0] == libvirt.VIR_DOMAIN_RUNNING
    }


@pass_connection
def create_disk(connection, name, size, format="qcow2"):
    with open("xmls/storage.xml", "r") as f:
        stgvol_xml_raw = f.read()

    stgvol_xml = stgvol_xml_raw.format(name=name, size=size, format=format)
    pool = connection.conn.storagePoolLookupByName("default")
    try:
        return pool.createXML(stgvol_xml, 0)
    except Exception:
        return False


@pass_connection
def create_appliance(connection, name, base_img, db_img, memory):
    with open("xmls/appliance.xml", "r") as f:
        app_xml_raw = f.read()
    app_xml = app_xml_raw.format(name=name, base_img=base_img, db_img=db_img, memory=str(memory))
    dom = connection.conn.defineXML(app_xml)
    if dom:
        return dom
    else:
        return False


@cli.command(help="Appliance Info")
@click.option("-a", "--all", is_flag=True, help="This return name of all appliances")
@pass_connection
def ps(connection, all):
    if all:
        data = [_vm_info(domain) for domain in connection.conn.listAllDomains()]
        for index, info in enumerate(data):
            if not index:
                click.echo(
                    "{:<5s}{:<20s}{:^10s}{:^15s}".format("Id", "Name", "Status", "Hostname")
                )
            click.echo(
                "{:<5s}{:<20s}{:^10s}{:^15s}".format(
                    str(info["id"]), info["name"], info["state"], info["hostname"]
                )
            )


@cli.command(help="Start Appliance")
@click.option("--name", prompt="Appliance name please")
@pass_connection
def start(connection, name):
    domains = {item.name(): item for item in connection.conn.listAllDomains()}
    try:
        dom = domains[name]
        if dom.create() < 0:
            click.echo("Appliance booting  fails")
    except Exception:
        click.echo("Select from appliance: ")
        for app_name in _vm_not_running():
            click.echo(app_name)


@cli.command(help="Stop Appliance")
@click.option(
    "--name",
    default=None,
    prompt="Appliance Name|Id please",
    help="Stop Appliance by providing Name",
)
@pass_connection
def stop(connection, name):
    domains = {item.name(): item for item in connection.conn.listAllDomains()}

    try:
        id = int(name)
        dom = connection.conn.lookupByID(id)
        dom.shutdown()
    except ValueError:
        if stop in _vm_running().keys():
            dom = domains[name]
            dom.shutdown()
        else:
            click.echo("Select from running appliance: ")
            for id, app_name in _vm_running().items():
                click.echo("{id} ==> {name}".format(id=str(id), name=app_name))


@cli.command(help="Kill Appliance")
@click.option(
    "--name",
    default=None,
    prompt="Appliance Name|Id please",
    help="Kill Appliance",
)
@pass_connection
def kill(connection, name):
    try:
        id = int(name)
        dom = connection.conn.lookupByID(id)
    except ValueError:
        dom = connection.conn.lookupByName(name)

    if dom:
        storage_db = {item.name(): item for item in connection.pool.listAllVolumes()}
        raw_xml = dom.XMLDesc(0)
        root = ET.fromstring(raw_xml)
        for disk in root.findall("devices/disk"):
            source = disk.find("source").get("file")
            file = source.split("/")[-1]
            if file in storage_db.keys():
                storage = storage_db[file]
                click.echo("Deleting disk '{source}'...".format(source=file))
                storage.delete()
        dom.undefine()
    else:
        click.echo("Please select proper Name or Id of appliance")


@cli.command()
@click.option("-l", "--local", is_flag=True, help="All available images")
@click.option("-r", "--remote", is_flag=True, help="All available remote images")
@click.option("-v", "--version", type=click.Choice(["5.9", "5.10"]), prompt="Appliance Version")
def images(local, remote, version):
    img_dir = "{home}/.miqbox".format(home=os.environ["HOME"])
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    if local:
        for img in os.listdir(img_dir):
            if version in img:
                click.echo(img)
    if remote:
        url = BASE_REPO.format(ver=version)
        for img in get_repo_img(url=url):
            click.echo(img)


@cli.command(help="Download Image")
@click.option("-n", "--name", prompt="Remote Image Name")
def pull(name, url=None):
    base_url = "{base}/{name}"
    if "5.9" in name:
        base = BASE_REPO.format(ver="5.9")
        url = base_url.format(base=base, name=name)
    elif "5.10" in name:
        base = BASE_REPO.format(ver="5.10")
        url = base_url.format(base=base, name=name)
    else:
        click.echo("Provide proper Image name, use 'miqbox images -r'")
    if url:
        if name not in os.listdir(IMG_DIR):
            download_img(url=url)
        else:
            click.echo("{img} already available".format(img=name))


@cli.command(help="Remove downloaded Image")
@click.option("-n", "--name", prompt="Image Name")
def rmi(name):
    if name in os.listdir(IMG_DIR):
        os.system("rm -rf {img_dir}/{name}".format(img_dir=IMG_DIR, name=name))
    else:
        click.echo("{img} not available".format(img=name))


@cli.command(help="Create Appliance")
@click.option("--name", prompt="Appliance name please")
@click.option("--image", prompt="Image name please")
@click.option("--memory", default=4, prompt="Memory in GiB")
@click.option("--db_space", default=8, prompt="Database size in GiB")
@pass_connection
def create(connection, name, image, memory, db_space, db=None):
    db_disk_name = "{app_name}-db".format(app_name=name)
    base_img = "{name}.qcow2".format(name=name)
    if image in os.listdir(IMG_DIR):
        os.system("sudo cp {img_dir}/{img} /var/lib/libvirt/images/{name}".format(
            img_dir=IMG_DIR,
            img=image,
            name=base_img)
        )
    else:
        click.echo("Image '{img}' not available...".format(img=image))
        return 0

    click.echo("Creating Database disk...")

    try:
        db = create_disk(name=db_disk_name, size=db_space)
        click.echo("'{}' created successfully".format(db_disk_name))
    except Exception:
        click.echo("Database disk creation fails")

    if db:
        click.echo("Creating appliance")
        dom = create_appliance(name=name, base_img=base_img, db_img=db.name(), memory=memory)
        if dom:
            dom.create()
            click.echo("Appliance {name} created successfully...".format(name=dom.name()))
        else:
            click.echo("Fail to create appliance...")

    if click.confirm("Configure appliance?"):
        click.echo("Waiting for getting  hostname....")

        timeout = time.time() + 300
        while True:
            host = _vm_info(dom)['hostname']
            if '--' not in host or time.time() > timeout:
                break
        config(host=host)
