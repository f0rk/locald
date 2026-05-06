import datetime
import logging
import shlex
import signal
import subprocess
import time

import psutil


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

            if self.process is not None:

                file_handles = [
                    self.process.stdout,
                    self.process.stderr,
                ]

                for file_handle in file_handles:
                    if hasattr(file_handle, "close"):
                        try:
                            file_handle.close()
                        except:
                            pass

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

        popen_args = {}
        if self.config["service"].get("log_path"):
            log_fp = open(self.config["service"]["log_path"], "ab+", buffering=0)
            popen_args = {
                "stdout": log_fp,
                "stderr": subprocess.STDOUT,
            }

        args = shlex.split(self.config["service"]["command"])
        self.process = subprocess.Popen(
            args,
            **popen_args,
        )
        self.dead_since = None
        self.was_killed = False

    def get_returncode(self):
        if self.process is None:
            return None

        return self.process.poll()

    def kill(self, timeout=5):
        if self.process is None:
            return

        parent = psutil.Process(self.process.pid)
        to_kill = parent.children(recursive=True)
        to_kill.append(parent)

        # First, try SIGTERM for graceful shutdown
        logger.info(
            "[locald] sending SIGTERM to service {} (pid {})"
            .format(self.name, self.process.pid)
        )
        for p in to_kill:
            try:
                p.send_signal(signal.SIGTERM)
            except psutil.NoSuchProcess:
                pass

        # Wait for processes to terminate gracefully
        start_time = time.time()
        still_alive = list(to_kill)
        
        while still_alive and (time.time() - start_time) < timeout:
            still_alive = [p for p in still_alive if p.is_running()]
            if still_alive:
                time.sleep(0.1)
        
        # If any processes are still alive, send SIGKILL
        if still_alive:
            logger.info(
                "[locald] sending SIGKILL to service {} (pid {}) - graceful shutdown timed out"
                .format(self.name, self.process.pid)
            )
            for p in still_alive:
                try:
                    p.send_signal(signal.SIGKILL)
                except psutil.NoSuchProcess:
                    pass
            
            self.process.kill()
        else:
            logger.info(
                "[locald] service {} (pid {}) terminated gracefully"
                .format(self.name, self.process.pid)
            )

        self.was_killed = True

    def is_running(self):
        if self.process is None:
            return False

        return self.get_returncode() is None

    def restart(self):
        self.kill()
        self.tend()
        self.start()
