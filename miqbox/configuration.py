import os
import subprocess
from collections import namedtuple

import click
from ruamel.yaml import safe_dump
from ruamel.yaml import safe_load

HOME = os.environ["HOME"]
USER = os.environ["USER"]


class Configuration(object):
    """Configure MiqBox.

    Args:
        conf (str): configuration file path.
    """

    def __init__(self, conf=None):
        self.conf_file = conf or os.path.join(os.path.dirname(__file__), "config.yaml")
        self.create_dict()

    def create_dict(self):
        """Create basic directories if not available."""

        for d in (self.image_path, self.libvirt.pool_path):
            if not os.path.isdir(d):
                subprocess.call(["sudo", "mkdir", "-p", d])
                subprocess.call(["sudo", "chown", USER, d])

    def read(self):
        """Read configuration file.

        Returns:
            dict: configuration data.
        """
        with open(self.conf_file, "r") as ymlfile:
            return safe_load(ymlfile)

    def write(self, cfg):
        """Write data to configuration file.

        Args:
            cfg (dict): configuration to save.
        """
        with open(self.conf_file, "w") as ymlfile:
            safe_dump(cfg, ymlfile, default_flow_style=False)

    @property
    def data(self):
        """Simple property pointing configuration data."""
        return self.read()

    @property
    def credentials(self):
        """Credentials from configuration"""

        Credentials = namedtuple("Credentials", ["username", "password"])
        return Credentials(self.data["appliance"]["username"], self.data["appliance"]["password"])

    @property
    def image_path(self):
        """image path in configuration."""
        return self.data.get("images").replace("~", HOME)

    @property
    def libvirt(self):
        """libvirt configuration data."""

        Libvirt = namedtuple("Libvirt", ["driver", "pool_name", "pool_path"])
        data = self.data.get("libvirt")
        return Libvirt(
            data.get("driver"),
            data["storage_pool"]["name"],
            data["storage_pool"]["path"].replace("~", HOME),
        )

    @property
    def repositories(self):
        """repositories configuration data"""

        Repositories = namedtuple("Repositories", ["url", "versions"])
        return {
            stream: Repositories(data.get("url"), data.get("versions"))
            for stream, data in self.data.get("repositories").items()
        }


@click.command(help="Configure MiqBox")
def config():
    """Configure MiqBox"""

    conf = Configuration()
    cfg = conf.data

    cfg["libvirt"]["driver"] = click.prompt("Hypervisor drivers url", default=conf.libvirt.driver)
    cfg["libvirt"]["storage_pool"]["name"] = click.prompt(
        "Storage Pool Name", default=conf.libvirt.pool_name
    )
    cfg["libvirt"]["storage_pool"]["path"] = click.prompt(
        "Storage Pool Path", default=conf.libvirt.pool_path
    )
    cfg["images"] = click.prompt("Local Image Location", default=conf.image_path)
    cfg["repositories"]["upstream"]["url"] = click.prompt(
        "Upstream Repository", default=conf.repositories.get("upstream").url
    )

    if click.confirm("Do you want to set downstream repository?"):
        cfg["repositories"]["downstream"]["url"] = click.prompt(
            "Downstream Repository", default=conf.repositories.get("downstream").url
        )

    conf.write(cfg=cfg)
    click.echo(click.style("Configuration saved successfully...", fg="green"))
