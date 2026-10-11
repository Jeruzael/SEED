"""Run with python -m dashboard. There is deliberately no --host option."""
import argparse
import os
from pathlib import Path


def server_options(port: int) -> dict:
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError('Port must be an integer between 1024 and 65535')
    return {'host':'127.0.0.1','port':port,'access_log':False,'proxy_headers':False}


def main():
    import uvicorn
    from .app import create_app
    parser = argparse.ArgumentParser(description='SEED local observatory')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--operator',action='store_true')
    parser.add_argument('--evaluation-root',type=Path,default=None,
                        help='Explicit evaluator-owned artifact root (read-only observer)')
    args = parser.parse_args()
    home = Path(os.environ.get('SEED_HOME',Path.home()/'Library/Application Support/SEED'))
    evaluation_root = args.evaluation_root
    if evaluation_root is None and os.environ.get('SEED_EVALUATION_ROOT'):
        evaluation_root = Path(os.environ['SEED_EVALUATION_ROOT'])
    options = server_options(args.port)
    uvicorn.run(create_app(home,args.port,args.operator,evaluation_root),**options)


if __name__ == '__main__':
    main()
