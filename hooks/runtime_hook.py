import sys
import time


def show_progress():
    for i in range(5):
        sys.stderr.write(f"\rLoading... [{'.' * i}]")
        time.sleep(0.1)
    sys.stderr.write("\n")


show_progress()
