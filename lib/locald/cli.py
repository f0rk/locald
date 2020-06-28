# Copyright 2020, Ryan P. Kelly.

import argparse
import os.path

from locald.manager import Manager


class App(object):

    def run(self):

        parser = argparse.ArgumentParser()

        parser.add_argument(
            "--config",
            help="path to locald configuration file",
        )

        subparsers = parser.add_subparsers(dest="command")

        start_parser = subparsers.add_parser("start")
        start_parser.set_defaults(func=self.start)

        stop_parser = subparsers.add_parser("stop")
        stop_parser.set_defaults(func=self.stop)

        status_parser = subparsers.add_parser("status")
        status_parser.set_defaults(func=self.status)

        args = parser.parse_args()

        returncode = args.func(config, products, args)

        return returncode

    def start(self, args):
        pass

    def stop(self, args):
        pass

    def status(self, args):
        pass
