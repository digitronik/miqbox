import libvirt

from miqbox.configuration import Configuration


class Client(Configuration):
    """Libvirt client

    Args:
        url (str): driver url
    """

    def __init__(self, url=None, *args, **kwargs):
        super(Client, self).__init__(*args, **kwargs)
        self.url = url or self.libvirt.driver

    @property
    def driver(self):
        """libvirt open connection"""
        try:
            return libvirt.open(self.url)
        except libvirt.libvirtError:
            print(f"Failed to open connection to {self.url}")
