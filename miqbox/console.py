import socket
import time
from distutils.version import LooseVersion

import click
import paramiko


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
            except Exception:
                # TODO: Include while implementing verbos
                pass
        else:
            return False

    def run_commands(self, commands, timeout=10):
        """run command with shell

        Args:
            commands (tuple): commands to run on appliance
            timeout (int): channel timeout default 10s
        """
        self.connect()
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
                pass

            # TODO: print results in proper verbose
            click.echo(result)

        self.client.close()

    def config_database(self):
        """Configure database"""
        db_conf = "7" if self.appliance.version <= LooseVersion("5.11") else "5"
        self.run_commands(("ap", "", db_conf, "1", "1", "1", "N", "0", "smartvm", "smartvm", "w"))

    def restart_server(self):
        """restart evm server"""
        evm_server = "15" if self.appliance.version < LooseVersion("5.10") else "17"
        self.run_commands(("ap", "", evm_server, "Y", ""))
