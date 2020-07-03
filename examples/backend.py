import sys
import time

while True:
    time.sleep(5)
    sys.stdout.write(str(time.time()))
    sys.stdout.write("\n")
    sys.stdout.flush()
