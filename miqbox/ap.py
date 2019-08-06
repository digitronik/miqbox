import socket
import time
from distutils.version import LooseVersion
import warnings

import click
import paramiko

# TODO: remove this as paramiko 2.4.2+ release comes. Its just for avoid warnings.
warnings.filterwarnings(action="ignore", module=".*paramiko.*")


class ApplianceConsole(object):
    """Configure appliance

    Reference:
    https://github.com/ManageIQ/integration_tests
    """

    def __init__(self, hostname, user, password, version):
        self.hostname = hostname
        self.user = user
        self.password = password
        self.version = version
        self.client = paramiko.SSHClient()
        self.channel = None

    def connect(self, timeout=60):
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        timeout_start = time.time()
        while time.time() < timeout_start + timeout:
            try:
                self.client.connect(
                    hostname=self.hostname, username=self.user, password=self.password
                )
                return True
            except Exception:
                # ToDo: Include while implementing verbos
                pass
        else:
            return False

    def run_commands(self, commands, autoreturn=True, timeout=10):
        if not self.channel:
            self.channel = self.client.invoke_shell()
        for command in commands:
            if command == "w":
                timeout = 300
            self.channel.settimeout(timeout)
            if autoreturn:
                command = command + "\n"
            self.channel.send(command)
            result = ""
            try:
                while True:
                    result += self.channel.recv(1).decode("ascii")
                    if "Press any key to continue" in result:
                        break
            except socket.timeout:
                pass
            # ToDo: print results in proper verbose
            click.echo(result)

    def db_config(self):
        db_conf = "5" if LooseVersion(self.version) < LooseVersion("5.10") else "7"
        self.run_commands(("ap", "", db_conf, "1", "1", "1", "N", "0", "smartvm", "smartvm", "w"))

    def server_restart(self):
        evm_server = "15" if LooseVersion(self.version) < LooseVersion("5.10") else "17"
        self.run_commands(("ap", "", evm_server, "Y", ""))


if __name__ == "__main__":
    ap = ApplianceConsole(hostname="192.168.122.37", user="root", password="foo", version="5.11")
    ap.connect()
    ap.run_commands(("ap", "", "7", "1", "1", "1", "N", "", "0", "smartvm", "smartvm"))
