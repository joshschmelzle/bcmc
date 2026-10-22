# -*- coding: utf-8 -*-
#  _
# | |__   ___ _ __ ___   ___
# | '_ \ / __| '_ ` _ \ / __|
# | |_) | (__| | | | | | (__
# |_.__/ \___|_| |_| |_|\___|
#
# bcmc: is a broadcast and multicast validator tool

# stdlib imports
import signal
import sys
import time

# our app imports
from .appsetup import setup_parser
from .broadcast import BroadcastListener, BroadcastServer
from .helpers import ServiceExit
from .multicast import MulticastListener, MulticastServer


def _shutdown(signal, frame):
    print("\nStop requested ...")
    raise ServiceExit


# register event handlers to trigger shutdown request
signal.signal(signal.SIGINT, _shutdown)
signal.signal(signal.SIGTERM, _shutdown)


def build_client_threads(args):
    """Receivers for client mode. ``args.host`` is the --bind address."""
    threads = []
    if args.broadcast:
        threads.append(BroadcastListener(args.port, args.debug, host=args.host))
    if args.multicast:
        threads.append(
            MulticastListener(args.group, args.port, args.debug, host=args.host)
        )
    return threads


def build_server(args):
    """Sender for server mode. ``args.host`` is the --bind address."""
    if args.broadcast:
        return BroadcastServer(
            args.port,
            args.padding,
            args.interval,
            dscp=args.dscp,
            debug=args.debug,
            host=args.host,
            payload=args.payload,
        )
    if args.multicast:
        return MulticastServer(
            args.group,
            args.port,
            args.padding,
            args.interval,
            args.ttl,
            dscp=args.dscp,
            debug=args.debug,
            host=args.host,
            payload=args.payload,
        )
    return None


def _tolerate_unencodable_output():
    """Replace characters the console can't encode instead of crashing.

    Windows consoles and redirected output often use a legacy code page such
    as cp1252, which can't encode the help epilog's heart.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def main():
    _tolerate_unencodable_output()
    parser = setup_parser()
    args = parser.parse_args()
    if not args.client and not args.server:
        print("bcmc: argument error - must either be a client (-c) or server (-s)")
        print("")
        parser.print_help()
        exit(1)
    if not args.broadcast and not args.multicast:
        print(
            "bcmc: argument error - must specify either broadcast (-bc) or multicast (-mc)"
        )
        print("")
        parser.print_help()
        exit(1)
    threads = []
    try:
        if args.client:
            # do client mode stuff.
            threads.extend(build_client_threads(args))
            # start threads
            for t in threads:
                t.start()

        if args.server:
            # do server mode stuff
            server = build_server(args)
            if args.broadcast:
                server.broadcast()
            if args.multicast:
                server.multicast()

        # Wait for a shutdown signal without spinning the CPU. SIGINT and
        # SIGTERM raise ServiceExit in the main thread, even during sleep.
        while True:
            time.sleep(1)
    except ServiceExit:
        for t in threads:
            t.stop_event.set()
        for t in threads:
            worker = getattr(t, "thread", None)
            if worker is not None:
                worker.join(timeout=2)


if __name__ == "__main__":
    main()
