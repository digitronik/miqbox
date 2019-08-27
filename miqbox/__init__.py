import click

from miqbox.configuration import config
from miqbox.images import images
from miqbox.images import pull
from miqbox.images import rmi
from miqbox.miqbox import create
from miqbox.miqbox import evmserver
from miqbox.miqbox import kill
from miqbox.miqbox import start
from miqbox.miqbox import status
from miqbox.miqbox import stop


@click.version_option()
@click.group()
def main():
    """Spin ManageIQ/CFME Appliance locally with Virtualization."""
    pass


# Image commands
main.add_command(images)
main.add_command(pull)
main.add_command(rmi)

# MiqBox command
main.add_command(status)

# Appliance operations commands
main.add_command(create)
main.add_command(start)
main.add_command(stop)
main.add_command(kill)
main.add_command(evmserver)

# Configuration command
main.add_command(config)


if __name__ == "__main__":
    main()
