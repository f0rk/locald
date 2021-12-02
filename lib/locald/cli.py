# Copyright 2020, Ryan P. Kelly.

import argparse
import os
import shutil
import sys
import time

from locald.client import Client
from locald.config import get_config, get_config_for_service
from locald.server import ensure_server, is_server_running, stop_server


class App(object):

    def run(self):

        parser = argparse.ArgumentParser()

        parser.add_argument(
            "--config",
            "-c",
            help="path to locald configuration file",
        )

        parser.add_argument(
            "--quiet",
            "-q",
            help="reduce the amount of output a command produces",
            action="store_true",
        )

        subparsers = parser.add_subparsers(dest="command")

        server_start_parser = subparsers.add_parser("server-start")
        server_start_parser.set_defaults(func=self.server_start)

        server_start_parser.add_argument(
            "--no-daemonize",
            action="store_true",
        )

        server_stop_parser = subparsers.add_parser("server-stop")
        server_stop_parser.set_defaults(func=self.server_stop)

        server_wait_parser = subparsers.add_parser("server-wait")
        server_wait_parser.add_argument(
            "--timeout",
            "-t",
            help="wait timeout (in seconds)",
            default=10,
            type=float,
        )
        server_wait_parser.set_defaults(func=self.server_wait)

        server_status_parser = subparsers.add_parser("server-status")
        server_status_parser.set_defaults(func=self.server_status)

        start_parser = subparsers.add_parser("start")
        start_parser.set_defaults(func=self.start)

        start_parser.add_argument("name")

        stop_parser = subparsers.add_parser("stop")
        stop_parser.set_defaults(func=self.stop)

        stop_parser.add_argument("name")

        restart_parser = subparsers.add_parser("restart")
        restart_parser.set_defaults(func=self.restart)

        restart_parser.add_argument("name")

        status_parser = subparsers.add_parser("status")
        status_parser.set_defaults(func=self.status)

        status_parser.add_argument("names")

        logs_parser = subparsers.add_parser("logs")
        logs_parser.set_defaults(func=self.logs)

        logs_parser.add_argument(
            "--no-follow",
            action="store_true",
        )

        logs_parser.add_argument("names")

        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            sys.exit(0)

        config = get_config(args.config)

        returncode = args.func(config, args)

        return returncode

    def get_services(self, config, args_names):

        names = [n.strip() for n in args_names.split(",") if n.strip()]

        if "ALL" in names:
            for key, values in config.items():
                if "service_path" in values:
                    names.append(key)

            names.remove("ALL")
            names = list(set(names))

        return names

    def start(self, config, args):
        client = Client(config)
        client.start(args.name, quiet=args.quiet)

    def stop(self, config, args):
        client = Client(config)
        client.stop(args.name, quiet=args.quiet)

    def restart(self, config, args):
        client = Client(config)
        client.restart(args.name, quiet=args.quiet)

    def status(self, config, args):
        client = Client(config)
        client.status(args.names)

    def server_start(self, config, args):
        ensure_server(config, args)

    def server_stop(self, config, args):
        if is_server_running(config):

            client = Client(config)

            names = self.get_services(config, "ALL")
            for name in names:
                client.stop(name, quiet=args.quiet)

            stop_server(config)

    def server_wait(self, config, args):
        start_time = time.time()
        while time.time() - start_time < args.timeout:
            if (
                is_server_running(config)
                and os.path.exists(config["locald"]["socket_path"])
            ):
                return

            time.sleep(0.1)

        raise Exception("Timeout while waiting for the server")


    def server_status(self, config, args):
        if is_server_running(config):
            sys.stdout.write("daemon is running\n")
            sys.stdout.flush()
            sys.exit(0)
        else:
            sys.stdout.write("daemon NOT running\n")
            sys.stdout.flush()
            sys.exit(1)

    def logs(self, config, args):

        names = self.get_services(config, args.names)

        log_paths = []
        for name in names:
            service_config = get_config_for_service(config, name)

            if "log_path" not in service_config["service"]:
                continue

            log_paths.append(service_config["service"]["log_path"])

        if not log_paths:
            if not args.quiet:
                sys.stderr.write("NO logs to tail\n")
                sys.stderr.flush()
                sys.exit(1)

        tail_args = [
            "tail",
        ]

        if not args.no_follow:
            tail_args.append("-F")

        tail_args.extend(log_paths)

        exec_path = shutil.which(tail_args[0])

        os.execv(exec_path, tail_args)
