import socket
import paramiko

strUser = "root"
strPwd = "smartvm"


class ApplianceConsole(object):

    def __init__(self, appliance):
        self.appliance = appliance
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(hostname=self.appliance, username=strUser, password=strPwd)

    def run_commands(self, commands, autoreturn=True, timeout=10, channel=None):
        if not channel:
            channel = self.client.invoke_shell()
        for command in commands:
            channel.settimeout(timeout)
            if autoreturn:
                command = (command + "\n")
            channel.send(command)
            result = ""
            try:
                while True:
                    result += channel.recv(1)
                    if "Press any key to continue" in result:
                        break
            except socket.timeout:
                pass
            print(result)

if __name__ == "__main__":
    ap = ApplianceConsole("192.168.122.37")
    ap.run_commands(("ap", "", "7", "1", "1", "N", "", "0", "smartvm", "smartvm", ""))