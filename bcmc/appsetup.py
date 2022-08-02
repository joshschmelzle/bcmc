# -*- coding: utf-8 -*-
#
# appsetup.py: provide application setup for bcmc


import argparse

from .__version__ import __author__, __version__


def port(value):
    # validate user port input is between 0 and 65535

    try:
        port = int(value)
        if port > 65535 or port < 0:
            raise argparse.ArgumentTypeError("port must be between 0 and 65535")
        return port
    except ValueError:
        raise argparse.ArgumentTypeError("port must be an integer")


def interval(value):
    # validate user interval input is a number or float

    try:
        float(value)
        return value
    except ValueError:
        raise argparse.ArgumentTypeError("interval must be an number like 1 or 0.5")


def dscp(value):
    # validate user dscp input is between 0 and 63

    dscp = int(value)
    if dscp > 63 or dscp < 0:
        raise argparse.ArgumentTypeError("dscp value must be between 0 and 63")
    return dscp


def isIPv4(ip):
    if ip:
        if str(int(ip)) == ip and 0 <= int(ip) <= 255:
            return True
    return False


def ip(ip):
    number_of_decimals = ip.count(".")
    decimals = ip.split(".")
    if (
        number_of_decimals >= 1
        and number_of_decimals <= 4
        and all(isIPv4(octet) for octet in decimals)
    ):
        if number_of_decimals == 1:
            return "{0}.0.0.{1}".format(decimals[0], decimals[1])
        if number_of_decimals == 2:
            return "{0}.0.{1}.{2}".format(decimals[0], decimals[1], decimals[2])
        return ip
    raise argparse.ArgumentTypeError("IP must be a valid IPv4 IP Address")


def setup_parser():
    # setup the argument parser for the application

    tag = "bcmc is a CLI-centric broadcast and multicast validation tool which can be run in client or server mode."
    info = "bcmc aims to function cross platform, but some optional features may not work on certain OSes."
    desc = "%(tag)s\r\n\r\n%(info)s" % locals()

    usage_head = "bcmc [-s|-c] [-bc|-mc] [options]"
    usage_foot = "       bcmc [-h|--help] [-v|--version]"
    usage_blurb = "%(usage_head)s\r\n%(usage_foot)s" % locals()

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=desc,
        epilog="Made with Python by {0}".format(__author__),
        fromfile_prefix_chars="@",
        usage=usage_blurb,
    )
    parser.add_argument(
        "-p",
        "--port",
        dest="port",
        type=port,
        metavar="2002",
        default="2002",
        help="port to listen on/connect to",
    )
    parser.add_argument(
        "-b",
        "--bind",
        dest="host",
        metavar="<host>",
        default=None,
        type=ip,
        help="bind to the interface associated with provided <host> address (experimental)",
    )
    parser.add_argument(
        "-v",
        "-version",
        "--version",
        action="version",
        version="%(prog)s {0}".format(__version__),
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        help="increase output for debugging purposes",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "-c",
        "--client",
        dest="client",
        action="store_true",
        default=False,
        help="run in client mode",
    )
    mode.add_argument(
        "-s",
        "--server",
        dest="server",
        action="store_true",
        default=False,
        help="run in client mode",
    )
    traffic_type = parser.add_mutually_exclusive_group()
    traffic_type.add_argument(
        "-bc",
        "--broadcast",
        dest="broadcast",
        action="store_true",
        default=False,
        help="set traffic type to broadcast",
    )
    traffic_type.add_argument(
        "-mc",
        "--multicast",
        dest="multicast",
        action="store_true",
        default=False,
        help="set traffic type to multicast",
    )
    parser.add_argument(
        "--group",
        dest="group",
        metavar="239.0.0.2",
        type=ip,
        default="239.0.0.2",
        help="multicast group address (239.0.0.2 by default)",
    )
    parser.add_argument(
        "-i",
        "--interval",
        dest="interval",
        metavar="1",
        type=interval,
        default="1",
        help="interval to send multicast packets",
    )
    parser.add_argument(
        "--dscp",
        dest="dscp",
        metavar="46",
        type=dscp,
        default=None,
        help="set the Differentiated Service Code Point value applied to packets sent in server mode",
    )
    parser.add_argument(
        "--padding",
        dest="padding",
        metavar="0",
        default="0",
        help="number of additional null bytes per payload sent in server mode",
    )
    return parser
