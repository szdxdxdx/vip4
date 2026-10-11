import argparse

import uvicorn

from app import config
from app.app import create_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default=config.HOST)
    parser.add_argument('--port', type=int, default=config.PORT)
    args = parser.parse_args()
    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
