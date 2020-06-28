# Copyright 2020, Ryan P. Kelly.

import argparse
import sys

from locald.client import Client
from locald.config import get_config
from locald.server import ensure_server, is_server_running, stop_server


class App(object):

    def run(self):

        parser = argparse.ArgumentParser()

        parser.add_argument(
            "--config",
            "-c",
            help="path to locald configuration file",
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

        server_status_parser = subparsers.add_parser("server-status")
        server_status_parser.set_defaults(func=self.server_status)

        start_parser = subparsers.add_parser("start")
        start_parser.set_defaults(func=self.start)

        start_parser.add_argument("name")

        stop_parser = subparsers.add_parser("stop")
        stop_parser.set_defaults(func=self.stop)

        stop_parser.add_argument("name")

        status_parser = subparsers.add_parser("status")
        status_parser.set_defaults(func=self.status)

        status_parser.add_argument("names")

        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            sys.exit(0)

        config = get_config(args.config)

        returncode = args.func(config, args)

        return returncode

    def start(self, config, args):
        client = Client(config)
        client.start(args.name)

    def stop(self, config, args):
        client = Client(config)
        client.stop(args.name)

    def status(self, config, args):
        client = Client(config)
        client.status(args.names)

    def server_start(self, config, args):
        ensure_server(config, args)

    def server_stop(self, config, args):
        stop_server(config)

    def server_status(self, config, args):
        if is_server_running(config):
            sys.stdout.write("daemon is running\n")
            sys.stdout.flush()
            sys.exit(0)
        else:
            sys.stdout.write("daemon NOT running\n")
            sys.stdout.flush()
            sys.exit(1)
