import datetime
import logging
import shlex
import subprocess


logger = logging.getLogger()


class Service(object):

    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.process = None
        self.dead_since = None
        self.was_killed = False

    def tend(self):
        returncode = self.get_returncode()
        if returncode is not None:
            logger.info(
                "[locald] service {} pid {} exited with {}"
                .format(self.name, self.process.pid, returncode)
            )
            self.process = None
            if not self.was_killed:
                self.dead_since = datetime.datetime.now()
        else:
            if self.dead_since:
                restart = self.config["service"].get("restart", "never")
                if restart == "always":

                    restart_seconds = int(self.config["service"].get("restart_seconds", "0"))

                    restart_time = (
                        self.dead_since
                        + datetime.timedelta(seconds=restart_seconds)
                    )

                    if datetime.datetime.now() >= restart_time:
                        self.start()

        return returncode

    def start(self):
        if self.process is not None:
            logger.info(
                "[locald] service {} is already running, not starting"
                .format(self.name)
            )
            return

        logger.info(
            "[locald] going to start service {}"
            .format(self.name)
        )

        args = shlex.split(self.config["service"]["command"])
        self.process = subprocess.Popen(args)
        self.dead_since = None
        self.was_killed = False

    def get_returncode(self):
        if self.process is None:
            return None

        return self.process.poll()

    def kill(self):
        if self.process is None:
            return

        self.process.kill()
        self.was_killed = True

    def is_running(self):
        if self.process is None:
            return False

        return self.get_returncode() is None
