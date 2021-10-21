import json
import logging
import logging.config
import os
import queue
import select
import socket
import traceback

from daemonize import Daemonize

from .config import get_config_for_service, get_service_configs
from .service import Service


logger = logging.getLogger()


class Socket(object):

    def __init__(self, path):
        self.path = path
        self.socket = None

    def __enter__(self):
        self.create()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.remove()

    def create(self):
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        try:
            os.unlink(self.path)
        except OSError:
            if os.path.exists(self.path):
                raise

        self.socket.bind(self.path)
        self.socket.listen()

    def remove(self):
        try:
            self.socket.close()
        except OSError:
            pass

        try:
            os.unlink(self.path)
        except OSError:
            pass


class Server(object):

    def __init__(self, config):
        self.config = config
        self.processes = {}

    def start(self):

        logging.config.fileConfig(self.config["locald"]["config_path"])

        try:
            return self._run()
        except:
            logger.error(traceback.format_exc())
            raise
        finally:
            for proc in self.processes.values():
                proc.kill()

    def _run(self):

        if "working_dir" in self.config["locald"]:
            os.chdir(self.config["locald"]["working_dir"])
        else:
            os.chdir(self.config["locald"]["config_dir"])

        socket_path = self.config["locald"]["socket_path"]

        logger.info(
            "[locald] going to begin listening on socket at {}"
            .format(socket_path)
        )

        timeout = 1  # 1 second

        with Socket(socket_path) as sock:

            inputs = [sock.socket]
            outputs = []
            messages_queue = {}

            while inputs:

                readable, writable, exceptional = select.select(
                    inputs,
                    outputs,
                    inputs,
                    timeout,
                )

                for s in readable:
                    if s is sock.socket:
                        connection, client_address = s.accept()
                        logger.info(
                            "[locald] new connection from {}"
                            .format(client_address)
                        )

                        connection.setblocking(0)
                        inputs.append(connection)

                        messages_queue[connection] = queue.Queue()
                    else:
                        data = s.recv(1024 * 1024)
                        if data:
                            logger.debug(
                                "[locald] received '{}' from {}"
                                .format(data, s.getpeername())
                            )
                            messages_queue[s].put(data)

                            if s not in outputs:
                                outputs.append(s)
                        else:
                            logger.info(
                                "[locald] closing {} after reading no data"
                                .format(s.getpeername())
                            )

                            if s in outputs:
                                outputs.remove(s)

                            inputs.remove(s)
                            s.close()

                            del messages_queue[s]

                for s in writable:

                    response = None

                    try:
                        next_message = messages_queue[s].get_nowait()
                        response = self.process_message(next_message)
                    except KeyError:
                        logger.warning(
                            "[locald] output queue for {} is missing"
                            .format(s)
                        )
                    except queue.Empty:
                        logger.info(
                            "[locald] output queue for {} is empty"
                            .format(s.getpeername())
                        )
                        outputs.remove(s)
                    else:
                        logger.debug(
                            "[locald] sending '{}' to {}"
                            .format(response, s.getpeername())
                        )
                        s.send(response)

                for s in exceptional:
                    logger.info(
                        "[locald] handling exceptional condition for {}"
                        .format(s.getpeername())
                    )
                    inputs.remove(s)
                    if s in outputs:
                        outputs.remove(s)
                    s.close()

                    del messages_queue[s]

                self.tend_processes()

    def process_message(self, message):

        message = message.decode("utf-8")
        data = json.loads(message)

        if "command" in data:
            command = data["command"]

            if command == "start":
                response = self.handle_start(data)
            elif command == "stop":
                response = self.handle_stop(data)
            elif command == "restart":
                response = self.handle_restart(data)
            elif command == "status":
                response = self.handle_status(data)
            else:
                response = self.handle_unknown(data)
        else:
            response = self.handle_unknown(data)

        response = json.dumps(response).encode("utf-8")
        return response

    def handle_start(self, command):

        name = command["name"]

        if name not in self.config:
            return {
                "messages": ["unknown service '{}'".format(name)],
            }

        messages, _ = self.start_service(name)

        return {
            "messages": messages,
        }

    def start_service(self, name):

        service_config = get_config_for_service(self.config, name)

        requires = []
        if "requires" in service_config["service"]:
            requires = service_config["service"]["requires"]
            requires = [r.strip() for r in requires.split(",") if r.strip()]

        for require in requires:
            if require not in self.config:
                return ["unknown required service '{}'".format(require)], True

        messages = []

        for require in requires:
            sub_messages, is_error = self.start_service(require)
            messages.extend(sub_messages)
            if is_error:
                return messages, True

        if name not in self.processes:
            proc = Service(name, service_config)
            self.processes[name] = proc

        self.processes[name].start()

        messages.append("started '{}'".format(name))

        return messages, False

    def handle_stop(self, command):

        name = command["name"]

        if name not in self.config:
            return {
                "messages": ["unknown service '{}'".format(name)],
            }

        if name not in self.processes:
            message = "'{}' is not running".format(name)
        else:
            self.processes[name].kill()

            message = "kill signal sent to '{}'".format(name)

        return {
            "messages": [message],
        }

    def handle_restart(self, command):

        name = command["name"]

        if name not in self.processes:
            return self.handle_start(command)
        else:
            self.processes[name].restart()

            message = "restarted '{}'".format(name)

        return {
            "messages": [message],
        }

    def get_service_status(self, name):

        if name not in self.config:
            status = "UNKNOWN_SERVICE"
        elif name in self.processes:
            if self.processes[name].is_running():
                status = "RUNNING"
            else:
                status = "STOPPED"
        else:
            status = "NOT_STARTED"

        return status

    def handle_status(self, command):

        name = command["name"]

        if name == "ALL":
            names = get_service_configs(self.config).keys()
        else:
            names = [name]

        status = {name: self.get_service_status(name) for name in names}

        return status

    def handle_unknown(self, command):

        if "command" in command:
            message = "unknown command '{}'".format(command["command"])
        else:
            message = "invalid command '{}' received from client".format(command)

        return {
            "messages": [message],
        }

    def tend_processes(self):
        for proc in self.processes.values():
            proc.tend()


def get_pid(pid_path):

    with open(pid_path, "rt") as fp:
        pid = fp.read()

    pid = int(pid)

    return pid


def is_server_running(config):

    if not os.path.exists(config["locald"]["pid_path"]):
        return False

    try:
        pid = get_pid(config["locald"]["pid_path"])
    except ValueError:
        return False

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


def create_server(config):
    server = Server(config)
    return server


def create_daemon(config, server):

    pid_path = config["locald"]["pid_path"]

    daemon = Daemonize(
        app="locald",
        pid=pid_path,
        action=server.start,
    )

    return daemon


def ensure_server(config, args):
    if not is_server_running(config):
        server = create_server(config)

        if args.no_daemonize:
            pid_path = config["locald"]["pid_path"]
            try:
                with open(pid_path, "wt") as pid_fp:
                    pid_fp.write(str(os.getpid()))
                    pid_fp.flush()
                    server.start()
            finally:
                try:
                    os.unlink(pid_path)
                except:
                    pass
        else:
            daemon = create_daemon(config, server)
            daemon.start()


def stop_server(config):

    if not os.path.exists(config["locald"]["pid_path"]):
        return False

    pid = get_pid(config["locald"]["pid_path"])

    try:
        os.kill(pid, 2)
    except OSError:
        return False
    else:
        return True
