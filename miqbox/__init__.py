import click

from miqbox.configuration import config
from miqbox.images import images, pull, rmi


@click.version_option()
@click.group()
def main():
    """Spin ManageIQ/CFME Appliance locally with virtualization."""
    pass


# Image commands
main.add_command(images)
main.add_command(pull)
main.add_command(rmi)


# Configuration command
main.add_command(config)
