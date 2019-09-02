import logging

import libvirt

from miqbox.configuration import Configuration

logger = logging.getLogger(__name__)


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
            logger.info("Libvirt opening connection: %s", self.url)
            return libvirt.open(self.url)
        except libvirt.libvirtError:
            logger.error("Libvirt failed to open connection: %s", self.url)
