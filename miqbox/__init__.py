import click


@click.version_option()
@click.group()
def main():
    """Spin ManageIQ/CFME Appliance locally with virtualization."""
    pass
