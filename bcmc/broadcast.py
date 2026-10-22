# -*- coding: utf-8 -*-
#
# broadcast.py: provide broadcast class for bcmc

# stdlib imports
import platform
import socket
import threading
import time
from datetime import datetime

# app imports
from .helpers import (
    ServiceExit,
    bind_udp_receiver,
    bind_udp_sender,
    default_ipv4_address,
    enable_packet_info,
    interface_index_for_ipv4,
    is_multicast_address,
    recv_packet,
)


class BroadcastServer:
    # send a UDP IP broadcast to 255.255.255.255
    def __init__(
        self,
        port,
        padding,
        interval,
        dscp=0,
        debug=False,
        family=socket.AF_INET,
        host=None,
        payload=None,
    ):
        self.port = int(port)
        self.padding = int(padding)
        self.broadcast_address = "255.255.255.255"
        self.dscp = dscp
        self.interval = float(interval)
        self.family = family
        self.debug = debug
        # bind_address is only the explicit --bind value. self.host is also
        # the label embedded in the payload and falls back to the hostname.
        self.bind_address = host or None
        self.host = host
        if not self.host:
            self.host = socket.gethostname()
        self.stop_event = threading.Event()
        self.payload = payload

        try:
            # AF_INET is a socket for IP packets
            self.bc_server_sock = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
            )
        except OSError as e:
            print(f"Socket could not be created. Error Code : {e}")
            raise ServiceExit from e

        self.set_platform_socket_options()

        # Set timeout so the socket does not block indefinitely.
        self.bc_server_sock.settimeout(0.2)
        try:
            bind_udp_sender(self.bc_server_sock, self.bind_address, multicast=False)
        except ServiceExit:
            self.bc_server_sock.close()
            raise

        print(f"Sending with socket: {self.bc_server_sock}")

    def set_platform_socket_options(self):
        # Set socket to broadcasting mode
        self.bc_server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        if self.dscp > 0:
            self.tos = int(self.dscp) << 2
            print(
                "Attempt to apply markings to broadcast server socket with DSCP ({0}) and TOS ({1})".format(
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

        if platform.system() == "Linux":
            # Enable port reuse so we can run multiple clients and servers on single (host, port).
            self.bc_server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            return

        if platform.system() == "Darwin":
            # Enable port reuse so we can run multiple clients and servers on single (host, port).
            self.bc_server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            return

        raise ValueError(
            "{0} does not appear to be a supported platform".format(platform.system())
        )

    def source_address(self):
        """The address broadcasts are sent from, for debug and error output."""
        try:
            address = self.bc_server_sock.getsockname()[0]
        except OSError:
            address = None
        if not address or address == "0.0.0.0":
            return self.bind_address or "default interface"
        return address

    def build_payload(self, message):
        """The payload to send: --payload or the message, plus null padding."""
        body = self.payload if self.payload else message
        return body + "\0" * self.padding

    def broadcast(self):
        counter = 0
        try:
            while not self.stop_event.is_set():
                counter += 1
                now = datetime.now().strftime("%H:%M:%S.%f")[:-2]

                if self.debug:
                    payload_message = (
                        "broadcast from {0} ({1}) to {2}:{3} message {4} at {5}".format(
                            self.host,
                            self.source_address(),
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
                payload = self.build_payload(payload_message)
                self.bc_server_sock.sendto(
                    payload.encode(), (self.broadcast_address, self.port)
                )
                print(
                    "Sending broadcast ({0} bytes) -> {1}".format(
                        len(payload), payload_message
                    )
                )
                time.sleep(self.interval)
        except OSError as error:
            if "too long" in str(error).lower():
                print(
                    "Error: message with payload size of {0} bytes is too long to send.".format(
                        len(payload)
                    )
                )
            else:
                print(
                    "Error: {0} sending broadcast from {1}".format(
                        error, self.source_address()
                    )
                )
            raise ServiceExit
        finally:
            self.bc_server_sock.close()


class BroadcastListener(threading.Thread):
    def __init__(self, port, debug=False, host=None):
        super().__init__()
        self.port = int(port)
        self.bind_address = host or None
        self.host = host
        self.debug = debug
        if not self.host and platform.system() == "Windows":
            # Only Windows binds and joins on this address. Resolving the
            # hostname can stall for a long time on macOS, so skip it there.
            self.host = default_ipv4_address()
        self.buffer_size = 10240
        self.horizontal_rule = 0
        self.stop_event = threading.Event()

        # Setup socket
        self.bc_client_sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )

        # Set socket options
        self.set_platform_socket_options()

        # Block briefly on receive so the loop can check stop_event without
        # spinning the CPU.
        self.bc_client_sock.settimeout(0.5)

        self.bc_client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        try:
            bind_udp_receiver(
                self.bc_client_sock, self.bind_address, self.port, multicast=False
            )
        except ServiceExit:
            self.bc_client_sock.close()
            raise

        self.packet_info = enable_packet_info(self.bc_client_sock)
        self.interface_index = interface_index_for_ipv4(self.bind_address)

        print(f"Listening with socket: {self.bc_client_sock}")

    def set_platform_socket_options(self):
        if platform.system() == "Windows":
            return

        if platform.system() == "Linux":
            # Enable port reuse so we can run multiple clients and servers on single (host, port).
            self.bc_client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return

        if platform.system() == "Darwin":
            # Enable port reuse so we can run multiple clients and servers on
            # single (host, port). BSD needs SO_REUSEPORT to share a wildcard
            # UDP port between processes.
            self.bc_client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.bc_client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
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
                payload, address, ifindex, destination = recv_packet(
                    self.bc_client_sock, self.buffer_size, self.packet_info
                )
                if self.accepts(ifindex, destination):
                    self.on_packet(payload, address)
            except OSError:
                pass
        self.bc_client_sock.close()

    def accepts(self, ifindex, destination):
        """Drop multicasts, and packets from other interfaces under --bind."""
        if destination and is_multicast_address(destination):
            return False
        if self.interface_index and ifindex and ifindex != self.interface_index:
            return False
        return True

    def on_packet(self, payload, address):
        now = datetime.now().strftime("%H:%M:%S.%f")[:-2]
        data = payload.decode(errors="replace")
        text = data.rstrip("\0")
        padding = len(data) - len(text)
        suffix = " (+{0} padding bytes)".format(padding) if padding else ""
        print(
            "Receiving ({0} bytes) time {1} from {2}:{3}:\n -> {4}{5}\n".format(
                len(payload), now, address[0], address[1], text.strip(), suffix
            )
        )
