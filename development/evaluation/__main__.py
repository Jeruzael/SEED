"""Trusted B10 evaluation entry point: python -m development.evaluation."""
import sys

from .cli import main

if __name__ == '__main__':
    sys.exit(main())
