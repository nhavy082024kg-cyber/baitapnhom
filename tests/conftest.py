import os
import sys

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
TESTS = os.path.dirname(os.path.abspath(__file__))
for p in (SRC, TESTS):
    if p not in sys.path:
        sys.path.insert(0, p)
