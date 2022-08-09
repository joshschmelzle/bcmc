# -*- coding: utf-8 -*-
#
# broadcast.py: provide broadcast class for bcmc

# stdlib imports
import os
import platform
import socket
import threading
import time
from datetime import datetime

# app imports
from .helpers import ServiceExit


class BroadcastServer:
    # send a UDP IP broadcast to 255.255.255.255
    def __init__(
        self, port, padding, interval, dscp, debug, family=socket.AF_INET, host=None
    ):
        self.port = int(port)
        self.padding = 2 * int(padding)
        self.broadcast_address = "255.255.255.255"
        self.dscp = dscp
        self.interval = float(interval)
        self.family = family
        self.debug = debug
        self.host = host
        if not self.host:
            self.host = socket.gethostname()
        self.stop_event = threading.Event()

        try:
            # AF_INET is a socket for IP packets
            self.bc_server_sock = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
            )
        except socket.error as e:
            print("Socket could not be created. Error Code : %s" % e)
            raise ServiceExit

        # Set timeout so the socket does not block indefinitely.
        self.bc_server_sock.settimeout(0.2)

        self.set_platform_socket_options()
        
        print("Sending with socket: {0}".format(self.bc_server_sock))

    def set_platform_socket_options(self):
        # Set socket to broadcasting mode
        self.bc_server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        if self.dscp:
            self.tos = int(self.dscp) << 2
            if self.debug:
                print(
                    "Attempt sending packets with DSCP ({0}) and TOS ({1})".format(
                        self.dscp, self.tos
                    )
                )
            if self.family == socket.AF_INET:
                self.bc_server_sock.setsockopt(
                    socket.IPPROTO_IP, socket.IP_TOS, self.tos
                )
            elif self.family == socket.AF_INET6:
                self.bc_server_sock.setsockopt(
                    socket.IPPROTO_IPV6, socket.IPV6_TCLASS, self.tos
                )
            else:
                raise ValueError("Invalid family %d" % self.family)

        if platform.system() == "Windows":
            return

        if platform.system() == "Linux" or platform.system() == "Darwin":
            # Enable port reuse so we can run multiple clients and servers on single (host, port).
            self.bc_server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            return

        raise ValueError(
            "{0} does not appear to be a supported platform".format(platform.system())
        )

    def broadcast(self):
        counter = 0
        try:
            while not self.stop_event.is_set():
                counter += 1
                extra = ""
                if self.padding:
                    extra = " " * self.padding
                now = datetime.now().strftime("%H:%M:%S.%f")[:-2]

                if self.debug:
                    payload_message = (
                        "broadcast from {0} ({1}) to {2}:{3} message {4} at {5}".format(
                            self.host,
                            socket.inet_ntoa(
                                self.bc_server_sock.getsockopt(
                                    socket.IPPROTO_IP, socket.IP_MULTICAST_IF, 4
                                )
                            ),
                            self.broadcast_address,
                            self.port,
                            counter,
                            now,
                        )
                    )
                else:
                    payload_message = (
                        "broadcast from {0} to {1}:{2} message {3} at {4}".format(
                            self.host, self.broadcast_address, self.port, counter, now
                        )
                    )
                payload = payload_message + "{0}".format(extra)
                self.bc_server_sock.sendto(
                    payload.encode(), (self.broadcast_address, self.port)
                )
                print(
                    "Sending broadcast ({0} bytes) -> {1}".format(
                        len(payload), payload_message
                    )
                )
                time.sleep(self.interval)
        except socket.error as error:
            if "too long" in str(error).lower():
                print(
                    "Error: message with payload size of {0} bytes is too long to send.".format(
                        len(payload)
                    )
                )
            else:
                print(
                    "Error: {0} on interface for {1}".format(
                        error,
                        socket.inet_ntoa(
                            self.bc_server_sock.getsockopt(
                                socket.IPPROTO_IP, socket.SO_BROADCAST, 4
                            )
                        ),
                    )
                )
            raise ServiceExit
        finally:
            self.bc_server_sock.close()


class BroadcastListener(threading.Thread):
    def __init__(self, port, debug, host=None):
        threading.Thread.__init__(self)
        self.port = int(port)
        self.host = host
        self.debug = debug
        if not self.host:
            self.host = socket.gethostbyname(socket.gethostname())
        self.buffer_size = 10240
        self.horizontal_rule = 0
        self.stop_event = threading.Event()

        # Setup socket
        self.bc_client_sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )

        # Socket set to non-blocking
        self.bc_client_sock.setblocking(0)

        # Set socket options
        self.set_platform_socket_options()

        print("Listening with socket: {0}".format(self.bc_client_sock))

    def set_platform_socket_options(self):
        if self.host:
            self.bc_client_sock.bind((self.host, self.port))
        else:
            self.bc_client_sock.bind(("", self.port))
        self.bc_client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        if platform.system() == "Windows":
            return

        if platform.system() == "Linux" or platform.system() == "Darwin":
            # Enable port reuse so we can run multiple clients and servers on single (host, port).
            self.bc_client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return

        raise ValueError(
            "{0} does not appear to be a supported platform".format(platform.system())
        )

    def start(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.start()
        header = "Listening for broadcasts on port {0}".format(self.port)
        self.horizontal_rule = "-" * len(header)
        print(header)
        print(self.horizontal_rule)

    def run(self):
        while not self.stop_event.is_set():
            try:
                payload, address = self.bc_client_sock.recvfrom(self.buffer_size)
                self.on_packet(payload, address)
            except socket.error:
                pass
        self.bc_client_sock.close()

    def on_packet(self, payload, address):
        now = datetime.now().strftime("%H:%M:%S.%f")[:-2]
        data = payload.decode()
        print(
            "Receiving ({0} bytes) time {1} from {2}:{3}:\n -> {4}\n".format(
                len(data), now, address[0], address[1], data.strip()
            )
        )
