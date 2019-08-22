import click

from miqbox.configuration import config


@click.version_option()
@click.group()
def main():
    """Spin ManageIQ/CFME Appliance locally with virtualization."""
    pass


# config command
main.add_command(config)