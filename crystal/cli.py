"""Buyruqlar qatori interfeysi: `python -m crystal <buyruq>`."""

import argparse
from contextlib import closing
import json
import logging
import sqlite3
import sys

from . import __version__, db as database
from .config import Settings
from .domain import DomainError
from .service import OrderService


def build_parser(settings):
    parser = argparse.ArgumentParser(prog="crystal", description="Crystal Logistics")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--db", default=settings.db_path, help="SQLite fayli (CRYSTAL_DB_PATH)")
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="HTTP API serverini ishga tushirish")
    serve.add_argument("--host", default=settings.host)
    serve.add_argument("--port", type=int, default=settings.port)

    commands.add_parser("demo", help="Buyurtmani yaratishdan topshirishgacha ko‘rsatish")
    create = commands.add_parser("create", help="Buyurtma yaratish")
    create.add_argument("address")
    create.add_argument("--warehouse", type=int, default=1)
    for name in ("receive", "assign", "dispatch", "deliver", "track"):
        command = commands.add_parser(name)
        command.add_argument("code")
        if name == "assign":
            command.add_argument("courier")
    return parser


def run_command(service, args):
    if args.command == "demo":
        return service.run_demo()
    if args.command == "create":
        return service.create_order(args.address, args.warehouse)
    if args.command == "track":
        return service.track(args.code)
    if args.command == "assign":
        return service.assign(args.code, args.courier)
    return service.move(args.code, args.command)


def main(argv=None):
    try:
        settings = Settings.from_env()
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    args = build_parser(settings).parse_args(argv)
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )

    if args.command == "serve":
        from .api.server import serve
        serve(Settings(args.db, args.host, args.port, settings.log_level))
        return 0

    db_path = ":memory:" if args.command == "demo" else args.db
    try:
        with closing(database.connect(db_path)) as db:
            result = run_command(OrderService(db), args)
    except (DomainError, sqlite3.Error) as error:
        print(error, file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
