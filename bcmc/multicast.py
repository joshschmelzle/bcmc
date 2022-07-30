# -*- coding: utf-8 -*-
#
# multicast.py: provide multicast class for bcmc

# stdlib imports
import os
import socket
import struct
import threading
import time
from datetime import datetime

# app imports
from .helpers import ServiceExit


class MulticastServer:
    def __init__(self, group, port, padding, interval, dscp, host=None):
        self.group = group
        self.port = int(port)
        self.padding = int(padding)
        self.interval = float(interval)
        self.dscp = dscp
        self.stop_event = threading.Event()
        self.hostname = socket.gethostname()

        self.multicast_group = (self.group, self.port)
        self.mc_server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ttl = struct.pack("b", 3)
        self.mc_server_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

        # Enable port reuse so we can run multiple clients and servers on single (host, port).
        # Does not work on Windows
        if os.name != "nt":
            self.mc_server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        # Set timeout so the socket does not block indefinitely.
        self.mc_server_sock.settimeout(0.2)
        if self.dscp:
            self.tos = int(self.dscp) << 2
            # print("Sending packets with DSCP ({0}) and TOS ({1})".format(self.dscp, self.tos))
            self.mc_server_sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, self.tos)

    def multicast(self):
        counter = 0
        try:
            while not self.stop_event.is_set():
                counter += 1
                extra = ""
                if self.padding:
                    extra = " " * self.padding
                now = datetime.now().strftime("%H:%M:%S.%f")[:-2]
                payload_message = (
                    "multicast from {0} to {1}:{2} message {3} at {4}".format(
                        self.hostname,
                        self.multicast_group[0],
                        self.multicast_group[1],
                        counter,
                        now,
                    )
                )
                payload = payload_message + "{0}".format(extra)
                self.mc_server_sock.sendto(payload.encode(), self.multicast_group)
                print(
                    "Sending multicast ({0} bytes) -> {1}".format(
                        len(payload), payload_message
                    )
                )
                time.sleep(self.interval)
        except socket.error as error:
            if "too long" in str(error).lower():
                print(
                    "Error: message with payload size of {0} too long to send.".format(
                        len(payload)
                    )
                )
            else:
                print(
                    "Error: {0} on interface for {1}".format(
                        error,
                        socket.inet_ntoa(
                            self.mc_server_sock.getsockopt(
                                socket.IPPROTO_IP, socket.IP_MULTICAST_IF, 4
                            )
                        ),
                    )
                )
            raise ServiceExit
        finally:
            self.mc_server_sock.close()


class MulticastListener(threading.Thread):
    def __init__(self, group, port, host=None):
        threading.Thread.__init__(self)
        self.port = int(port)
        self.host = host
        if not self.host:
            self.host = socket.gethostbyname(socket.gethostname())
        self.group = group
        self.buffer_size = 10240
        self.horizontal_rule = 0
        self.stop_event = threading.Event()

        # setup IP socket
        self.socket = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )

        # Enable port reuse so we can run multiple clients and servers on single (host, port).
        # This does not work on Windows (nt)
        if os.name != "nt":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.socket.setblocking(0)

    def start(self):
        if os.name == "nt":
            self.socket.bind((self.host, self.port))
            self.socket.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_ADD_MEMBERSHIP,
                socket.inet_aton(self.group) + socket.inet_aton(self.host),
            )
        else:
            self.socket.bind(("", self.port))
            mreq = struct.pack("4sl", socket.inet_aton(self.group), socket.INADDR_ANY)
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        self.thread = threading.Thread(target=self.run)
        self.thread.start()
        header = "Listening for multicasts on group {0} port {1}".format(
            self.group, self.port
        )
        self.horizontal_rule = "-" * len(header)
        print(header)
        print(self.horizontal_rule)

    def run(self):
        while not self.stop_event.is_set():
            try:
                payload, address = self.socket.recvfrom(self.buffer_size)
                self.on_packet(payload, address)
            except socket.error:
                pass
        self.socket.close()

    def on_packet(self, payload, address):
        now = datetime.now().strftime("%H:%M:%S.%f")[:-2]
        data = payload.decode()
        print(
            "Receiving ({0} bytes) time {1} from {2}:{3}:\n -> {4}\n".format(
                len(data), now, address[0], address[1], data.strip()
            )
        )
