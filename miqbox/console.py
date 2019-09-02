import logging
import socket
import time
from distutils.version import LooseVersion

import paramiko

logger = logging.getLogger(__name__)


class Console(object):
    """Configure appliance

    Args:
        appliance (object): miqbox:Appliance object
    """

    def __init__(self, appliance):
        self.appliance = appliance
        self.client = paramiko.SSHClient()

    def connect(self, timeout=60):
        """make connection"""

        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        timeout_start = time.time()

        while time.time() < timeout_start + timeout:
            try:
                self.client.connect(
                    hostname=self.appliance.hostname,
                    username=self.appliance.creds.username,
                    password=self.appliance.creds.password,
                )
                logger.info(f"connected to '{self.appliance.hostname}'")
            except Exception:
                logger.debug(f"fail to connect '{self.appliance.hostname}'. trying again")
                pass
        else:
            logger.error(f"Fail to connect '{self.appliance.hostname}'")
            return False

    def run_commands(self, commands, timeout=10):
        """run command with shell

        Args:
            commands (tuple): commands to run on appliance
            timeout (int): channel timeout default 10s
        """
        self.connect()
        logger.info("Invocking channel")
        channel = self.client.invoke_shell()

        for command in commands:
            if command == "w":
                timeout = 180
            channel.settimeout(timeout)
            command = command + "\n"
            channel.send(command)
            result = ""
            try:
                while True:
                    result += channel.recv(1).decode("ascii")
                    if "Press any key to continue" in result:
                        break
            except socket.timeout:
                logger.error(f"socket timeout for command: '{command}'")
                pass

            logger.info(f"Command '{command}' output:\n '{result}'")

        self.client.close()

    def config_database(self):
        """Configure database"""
        logger.info(f"Configuring database of appliance: {self.appliance.name}")
        db_conf = "5" if self.appliance.version < LooseVersion("5.10") else "7"
        self.run_commands(("ap", "", db_conf, "1", "1", "1", "N", "0", "smartvm", "smartvm", "w"))

    def restart_server(self):
        """restart evm server"""
        logger.info(f"Restarting EVM server of appliance: {self.appliance.name}")
        evm_server = "15" if self.appliance.version < LooseVersion("5.10") else "17"
        self.run_commands(("ap", "", evm_server, "Y", ""))
