import json
import socket

from .server import is_server_running


class Client(object):

    def __init__(self, config):
        self.config = config

    def connect(self):

        socket_path = self.config["locald"]["socket_path"]

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path)

        return sock

    def prepare_data(self, data):

        raw_data = json.dumps(data)
        raw_data = raw_data.encode("utf-8")

        return raw_data

    def parse_response(self, raw_data):
        data = raw_data.decode("utf-8")
        data = json.loads(data)

        return data

    def send(self, sock, command):

        data = self.prepare_data(command)
        sock.sendall(data)

        raw_response = sock.recv(1024)  # XXX

        return self.parse_response(raw_response)

    def send_command(self, command):

        sock = None

        try:
            sock = self.connect()
            response = self.send(sock, command)
        except FileNotFoundError:
            if is_server_running(self.config):
                message = "sending command failed. are your socket permissions correct?"
            else:
                message = "sending command failed. server does not appear to be running."

            response = {
                "messages": [message],
            }

        finally:
            if sock is not None:
                sock.close()

        return response

    def start(self, name):

        command = {
            "command": "start",
            "name": name,
        }

        response = self.send_command(command)

        for message in response["messages"]:
            print(message)

    def stop(self, name):

        command = {
            "command": "stop",
            "name": name,
        }

        response = self.send_command(command)

        for message in response["messages"]:
            print(message)

    def status(self, names):

        command = {
            "command": "status",
            "name": names,
        }

        statuses = self.send_command(command)

        names = list(statuses.keys())
        names.sort()
        for name in names:
            print("{}: {}".format(name, statuses[name]))
