import socket
import time
from collections import namedtuple

import click
import paramiko

SSHOut = namedtuple("SSHOut", ["rc", "stdout", "stderr"])


class SSH(object):
    """Configure appliance

    Args:
        hostname: appliance ip
        username: username of appliance
        password: password of appliance
    """

    def __init__(self, hostname, username, password):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.client = paramiko.SSHClient()
        self.connect()

    def __del__(self):
        self.client.close()

    def connect(self, timeout=60):
        """create connection"""

        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        timeout_start = time.time()

        while time.time() < timeout_start + timeout:
            try:
                self.client.connect(
                    hostname=self.hostname, username=self.username, password=self.password,
                )
            except Exception:
                # TODO: Include while implementing verbos
                pass
        else:
            return False

    def run_commands(self, timeout=10, *commands):
        """run command with shell

        Args:
            commands: commands to run on appliance
            timeout (int): channel timeout default 10s
        """
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

    def run_command(self, command):
        channel = self.client.get_transport().open_session()
        session = True
        stdout = ""
        stderr = ""
        channel.exec_command(command)
        time.sleep(1)

        while session:
            if channel.recv_ready():
                stdout += channel.recv(1024).decode("ascii")
            if channel.recv_stderr_ready():
                stderr += channel.recv_stderr(1024).decode("ascii")
            if channel.exit_status_ready():
                rc = channel.recv_exit_status()
                session = False

        return SSHOut(rc=rc, stdout=stdout, stderr=stderr)
