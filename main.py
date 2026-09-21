#!/usr/bin/env python3
from pathlib import Path
import os
import signal
from seed.organism import SeedOrganism


def main():
    home = Path(os.environ.get('SEED_HOME', Path.home() / 'Library/Application Support/SEED'))
    organism = SeedOrganism(home)
    from seed.logging_setup import configure_logging
    configure_logging(home, 'seed', organism.config['log_bytes'], organism.config['log_count'])
    def stop_handler(signum, frame):
        organism.stop()
    signal.signal(signal.SIGTERM, stop_handler)
    signal.signal(signal.SIGINT, stop_handler)
    organism.run()


if __name__ == '__main__':
    main()
