import logging
import os
from logging.handlers import RotatingFileHandler
from .paths import checked_path


class SafeRotatingHandler(RotatingFileHandler):
    def _open(self):
        from pathlib import Path
        path = Path(self.baseFilename)
        checked_path(path.parent, path.name)
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        return os.fdopen(fd, 'a', encoding='utf-8')

    def doRollover(self):
        from pathlib import Path
        path = Path(self.baseFilename)
        for i in range(self.backupCount+1):
            checked_path(path.parent, path.name + (f'.{i}' if i else ''))
        super().doRollover()


def configure_logging(home, name='seed', max_bytes=5*1024**2, count=3):
    path = checked_path(home, name + '.log')
    logger = logging.getLogger(name)
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = SafeRotatingHandler(path, maxBytes=max_bytes, backupCount=count, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler)
    return logger
