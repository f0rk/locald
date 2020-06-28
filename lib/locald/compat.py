# Copyright 2020, Ryan P. Kelly.

"""
Python 2 to 3 compatability functions.
"""

import shutil
import tempfile


try:
    TemporaryDirectory = tempfile.TemporaryDirectory
except AttributeError:

    class TemporaryDirectory(object):

        def __init__(self):
            self.name = tempfile.mkdtemp()

        def __enter__(self):
            return self.name

        def __exit__(self, *args):
            self.cleanup()

        def cleanup(self):
            shutil.rmtree(self.name, ignore_errors=True)
