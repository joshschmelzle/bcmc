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


def main():
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
            if args.broadcast:
                # do client broadcast stuff.
                bc_rx = BroadcastListener(args.port, args.debug)
                threads.append(bc_rx)
            if args.multicast:
                # do client multicast stuff.
                mc_rx = MulticastListener(args.group, args.port, args.debug)
                threads.append(mc_rx)
        if args.server:
            # do server mode stuff
            if args.broadcast:
                # do server broadcast stuff.
                bc_tx = BroadcastServer(
                    args.port,
                    args.padding,
                    args.interval,
                    args.dscp,
                    args.debug,
                    host=args.host,
                )
                bc_tx.broadcast()
            if args.multicast:
                # do server multicast stuff.
                mc_tx = MulticastServer(
                    args.group,
                    args.port,
                    args.padding,
                    args.interval,
                    args.dscp,
                    args.debug,
                    host=args.host,
                )
                mc_tx.multicast()
        # start threads
        for t in threads:
            t.start()

        # loop until shutdown is triggered
        while True:
            pass
    except ServiceExit:
        for t in threads:
            t.stop_event.set()


if __name__ == "__main__":
    main()
