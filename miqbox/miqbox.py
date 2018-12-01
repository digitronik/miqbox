# Main file for project
import sys

import click
import libvirt


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
        print("Connected...")
    except Exception:
        click.echo("Failed to open connection to {}".format(url), file=sys.stderr)
        exit(1)
    try:
        connection.pool = connection.conn.storagePoolLookupByName("default")
    except Exception:
        click.echo("Failed to open storage pool...")
