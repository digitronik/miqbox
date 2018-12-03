import os
import time
import xml.etree.ElementTree as ET

import click
import libvirt
import requests
import yaml
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

home = os.environ["HOME"]


class Connection(object):
    def __init__(self):
        self.conn = None
        self.pool = None
        self.cfg = None


connection = click.make_pass_decorator(Connection, ensure=True)


@click.group()
@connection
def cli(connection):
    conf = Configuration()
    connection.cfg = conf.read()
    url = connection.cfg.get("hypervisor_driver")
    storage = connection.cfg.get("storage_pool")

    try:
        connection.conn = libvirt.open(url)
    except Exception:
        click.echo("Failed to open connection to {url}".format(url=url))
        exit(1)

    try:
        connection.pool = connection.conn.storagePoolLookupByName(storage)
    except Exception as e:
        click.echo("Failed to open storage pool {name}".format(name=storage))
        exit(1)


class Configuration(object):
    def __init__(self):
        self.conf_file = "{home}/.config/miqbox/conf.yml".format(home=home)
        dir_path = os.path.dirname(self.conf_file)
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)
        if not os.path.isfile(self.conf_file):
            raw_cfg = {
                'repository': {
                    'upstream': 'http://releases.manageiq.org/',
                    'downstream': 'None'},
                "local_image": "{home}/.miqbox".format(home=home),
                "libvirt_image": "/var/lib/libvirt/images/",
                "hypervisor_driver": "qemu:///system",
                "storage_pool": "default",
            }
            self.write(raw_cfg)

    def read(self):
        with open(self.conf_file, 'r') as ymlfile:
            return yaml.load(ymlfile)

    def write(self, cfg):
        with open(self.conf_file, 'w') as ymlfile:
            return yaml.dump(cfg, ymlfile, default_flow_style=False)


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
    img_dir = connection.cfg.get("local_image")
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    img_name = os.path.splitext(url)[-1]
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
    page = requests.get(url, verify=ssl_verify).text
    soup = BeautifulSoup(page, "html.parser")
    return [
        node.get("href") for node in soup.find_all("a") if node.get("href").endswith(extension)
    ]


@connection
def create_disk(connection, name, size, format="qcow2"):
    with open("xmls/storage.xml", "r") as f:
        stgvol_xml_raw = f.read()

    stgvol_xml = stgvol_xml_raw.format(name=name, size=size, format=format)
    pool = connection.conn.storagePoolLookupByName("default")
    try:
        return pool.createXML(stgvol_xml, 0)
    except Exception:
        return False


@connection
def create_appliance(connection, name, base_img, db_img, memory):
    with open("xmls/appliance.xml", "r") as f:
        app_xml_raw = f.read()
    app_xml = app_xml_raw.format(name=name, base_img=base_img, db_img=db_img, memory=str(memory))
    dom = connection.conn.defineXML(app_xml)
    if dom:
        return dom
    else:
        return False


@cli.command(help="Configure miqbox")
def config():
    conf = Configuration()
    cfg = conf.read()

    cfg["hypervisor_driver"] = click.prompt("Hypervisor drivers url", default=cfg.get("hypervisor_driver"))
    cfg["storage_pool"]= click.prompt("Storage Pool Name", default=cfg.get("storage_pool"))
    cfg["libvirt_image"] = click.prompt("Libvirt Image Location", default=cfg.get("libvirt_image"))
    cfg["local_image"] = click.prompt("Local Image Location", default=cfg.get("local_image"))

    if click.confirm("Do you want to set downstream repository?"):
        cfg["repository"]["downstream"] = click.prompt("Downstream Repository", default=cfg["repository"]["downstream"])

    conf.write(cfg=cfg)


@cli.command(help="Appliance Status")
@click.option("-a", "--all", is_flag=True, help="All Appliances")
@click.option("-r", "--running", is_flag=True, help="All Running Appliances")
@click.option("-s", "--stop", is_flag=True, help="All Stopped Appliances")
def status(all, running, stop):
    if all:
        status = None
    elif running:
        status = "running"
    elif stop:
        status = "shut off"

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
@click.option("-n", "--name", prompt="Appliance name please", help="Appliance Name")
@connection
def start(connection, name):
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


@cli.command(help="Stop Appliance")
@click.option("-n", "--name", default=None, prompt="Appliance Name|Id", help="Appliance Name")
@connection
def stop(connection, name):
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
@click.option("-n", "--name", default=None, prompt="Appliance Name please", help="Appliance Name")
@connection
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
                storage.delete()
                click.echo("Deleted disk '{source}'...".format(source=file))
        dom.undefine()
    else:
        click.echo("Please select proper Name or Id of appliance")


@cli.command()
@click.option("-l", "--local", is_flag=True, help="All available images")
@click.option("-r", "--remote", is_flag=True, help="All available remote images")
@connection
def images(connection, local, remote):
    img_dir = connection.cfg.get("local_image")
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    stream = click.prompt("stream:", default="downstream", type=click.Choice(["downstream",
                                                                   "upstream"]))
    base_repo = connection.cfg["repository"].get(stream)
    if stream == "downstream":
        ver = click.prompt("Version:", default="5.10", type=click.Choice(["5.8", "5.9", "5.10"]))
        extension = "qcow2"
    else:
        ver = "manageiq"
        extension = "qc2"

    if local:
        for img in os.listdir(img_dir):
            if ver in img:
                click.echo(img)

    if remote:
        if stream == "upstream":
            url = base_repo
        else:
            url = "{base_repo}/builds/cfme/{ver}/stable".format(base_repo=base_repo, ver=ver)

    for img in get_repo_img(url=url, extension=extension):
        click.echo(img)


@cli.command(help="Download Image")
@click.option("-n", "--name", prompt="Remote Image Name")
@connection
def pull(connection, name):
    if "manageiq" in name:
        stream = ver = "upstream"
    else:
        stream = "downstream"
        if "5.10" in name:
            ver = "5.10"
        elif "5.9" in name:
            ver = "5.9"
        elif "5.8" in name:
            ver = "5.8"

    base_repo = connection.cfg["repository"].get(stream)
    if stream == "upstream":
        url = "{base_repo}/{name}".format(base_repo=base_repo, name=name)
    else:
        url = "{base_repo}/builds/cfme/{ver}/stable/{name}".format(base_repo=base_repo, ver=ver,
                                                             name=name)

    if url:
        img_dir = connection.cfg.get("local_image")
        if name not in os.listdir(img_dir):
            download_img(url=url)
        else:
            click.echo("{img} already available".format(img=name))


@cli.command(help="Remove downloaded Image")
@click.option("-n", "--name", prompt="Image Name")
@connection
def rmi(connection, name):
    img_dir = connection.cfg.get("local_image")
    if name in os.listdir(img_dir):
        os.system("rm -rf {img_dir}/{name}".format(img_dir=img_dir, name=name))
    else:
        click.echo("{img} not available".format(img=name))


@cli.command(help="Create Appliance")
@click.option("--name", prompt="Appliance name please")
@click.option("--image", prompt="Image name please")
@click.option("--memory", default=4, prompt="Memory in GiB")
@click.option("--db_space", default=8, prompt="Database size in GiB")
@connection
def create(connection, name, image, memory, db_space, db=None):
    img_dir = connection.cfg.get("local_image")
    libvirt_dir = connection.cfg.get("libvirt_image")
    db_disk_name = "{app_name}-db".format(app_name=name)
    base_img = "{name}.{ext}".format(name=name, ext=os.path.splitext(image)[-1])

    if image in os.listdir(img_dir):
        os.system(
            "sudo cp {img_dir}/{img} {lib_dir}/{name}".format(
                img_dir=img_dir, img=image, lib_dir=libvirt_dir, name=base_img
            )
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
            host = _vm_info(dom)["hostname"]
            if "--" not in host or time.time() > timeout:
                break
        config(host=host)
