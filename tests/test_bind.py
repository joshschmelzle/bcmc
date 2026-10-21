# -*- coding: utf-8 -*-
"""--bind selects the interface used to send and receive."""

import errno
import socket
import sys
import unittest

from bcmc.appsetup import setup_parser
from bcmc.broadcast import BroadcastListener, BroadcastServer
from bcmc.helpers import (
    _IP_BOUND_IF,
    ServiceExit,
    interface_name_for_ipv4,
    ipv4_interfaces,
)
from bcmc.multicast import MulticastListener, MulticastServer


def multicast_if(sock):
    raw = sock.getsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, 4)
    return socket.inet_ntoa(raw)


def local_address(sock):
    """The socket's bound address. Windows raises for an unbound socket."""
    try:
        return sock.getsockname()[0]
    except OSError:
        return "0.0.0.0"


def recv_once(sock, timeout):
    sock.settimeout(timeout)
    try:
        return sock.recvfrom(65535)
    except socket.timeout:
        return None
    except OSError as exc:
        if exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
            return None
        raise


def send_broadcast(address, port, payload):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind((address, 0))
        sock.sendto(payload, ("255.255.255.255", port))
    finally:
        sock.close()


LINUX = sys.platform.startswith("linux")
MACOS = sys.platform == "darwin"
UNIX_PINNING = LINUX or MACOS
LOOPBACK = "lo0" if MACOS else "lo"


class BindTests(unittest.TestCase):
    def test_loopback_interface_lookup(self):
        if not UNIX_PINNING:
            self.skipTest("interface lookup is implemented for linux and macOS")
        self.assertEqual(interface_name_for_ipv4("127.0.0.1"), LOOPBACK)
        addresses = [ip for _name, ip in ipv4_interfaces()]
        self.assertIn("127.0.0.1", addresses)

    def test_broadcast_server_default_does_not_bind(self):
        server = BroadcastServer(9, 0, 1)
        self.addCleanup(server.bc_server_sock.close)
        self.assertIsNone(server.bind_address)
        self.assertEqual(local_address(server.bc_server_sock), "0.0.0.0")
        self.assertEqual(multicast_if(server.bc_server_sock), "0.0.0.0")

    def test_broadcast_server_bind_sets_source(self):
        server = BroadcastServer(9, 0, 1, host="127.0.0.1")
        self.addCleanup(server.bc_server_sock.close)
        self.assertEqual(server.bind_address, "127.0.0.1")
        self.assertEqual(server.bc_server_sock.getsockname()[0], "127.0.0.1")
        self.assertEqual(multicast_if(server.bc_server_sock), "127.0.0.1")

    def test_broadcast_server_rejects_nonlocal_bind(self):
        with self.assertRaises(ServiceExit):
            BroadcastServer(9, 0, 1, host="192.0.2.8")

    def test_multicast_server_bind_sets_interface(self):
        server = MulticastServer("239.255.1.1", 9, 0, 1, host="127.0.0.1")
        self.addCleanup(server.mc_server_sock.close)
        self.assertEqual(server.mc_server_sock.getsockname()[0], "127.0.0.1")
        self.assertEqual(multicast_if(server.mc_server_sock), "127.0.0.1")

    def test_multicast_server_default_interface_is_unspecified(self):
        server = MulticastServer("239.255.1.2", 9, 0, 1)
        self.addCleanup(server.mc_server_sock.close)
        self.assertIsNone(server.bind_address)
        self.assertEqual(local_address(server.mc_server_sock), "0.0.0.0")
        self.assertEqual(multicast_if(server.mc_server_sock), "0.0.0.0")

    def test_cli_bind_is_applied_to_broadcast_sockets(self):
        from bcmc.__main__ import build_client_threads, build_server

        server_args = setup_parser().parse_args(
            ["-s", "-bc", "--bind", "127.0.0.1", "-p", "9"]
        )
        server = build_server(server_args)
        self.addCleanup(server.bc_server_sock.close)
        self.assertEqual(server.bc_server_sock.getsockname()[0], "127.0.0.1")

        client_args = setup_parser().parse_args(
            ["-c", "-bc", "--bind", "127.0.0.1", "-p", "0"]
        )
        listener = build_client_threads(client_args)[0]
        self.addCleanup(listener.bc_client_sock.close)
        self.assertEqual(listener.bind_address, "127.0.0.1")

    def test_cli_bind_is_applied_to_multicast_sockets(self):
        from bcmc.__main__ import build_client_threads, build_server

        server_args = setup_parser().parse_args(
            [
                "-s",
                "-mc",
                "--bind",
                "127.0.0.1",
                "--group",
                "239.255.1.3",
                "-p",
                "9",
            ]
        )
        server = build_server(server_args)
        self.addCleanup(server.mc_server_sock.close)
        self.assertEqual(multicast_if(server.mc_server_sock), "127.0.0.1")

        client_args = setup_parser().parse_args(
            [
                "-c",
                "-mc",
                "--bind",
                "127.0.0.1",
                "--group",
                "239.255.1.4",
                "-p",
                "0",
            ]
        )
        listener = build_client_threads(client_args)[0]
        self.addCleanup(listener.mc_client_sock.close)
        self.assertEqual(listener.bind_address, "127.0.0.1")

    @unittest.skipUnless(LINUX, "linux loopback carries limited broadcasts")
    def test_broadcast_bind_source_and_receive_interface(self):
        listener = BroadcastListener(0, host="127.0.0.1")
        self.addCleanup(listener.bc_client_sock.close)
        port = listener.bc_client_sock.getsockname()[1]

        server = BroadcastServer(port, 0, 1, host="127.0.0.1")
        self.addCleanup(server.bc_server_sock.close)
        server.bc_server_sock.sendto(b"from-lo", ("255.255.255.255", port))
        got = recv_once(listener.bc_client_sock, 1.0)
        self.assertIsNotNone(got)
        payload, address = got
        self.assertEqual(payload, b"from-lo")
        self.assertEqual(address[0], "127.0.0.1")

        other = self._other_broadcast_source()
        if other is None:
            return
        send_broadcast(other, port, b"from-other")
        self.assertIsNone(recv_once(listener.bc_client_sock, 0.4))

    @unittest.skipUnless(UNIX_PINNING, "uses linux or macOS multicast delivery")
    def test_multicast_bind_receive_interface(self):
        group = "239.255.1.5"
        listener = MulticastListener(group, 0, host="127.0.0.1")
        self.addCleanup(listener.mc_client_sock.close)
        port = listener.mc_client_sock.getsockname()[1]

        server = MulticastServer(group, port, 0, 1, host="127.0.0.1")
        self.addCleanup(server.mc_server_sock.close)
        server.mc_server_sock.sendto(b"from-lo", (group, port))
        got = recv_once(listener.mc_client_sock, 1.0)
        self.assertIsNotNone(got)
        payload, address = got
        self.assertEqual(payload, b"from-lo")
        self.assertEqual(address[0], "127.0.0.1")

        other = self._other_multicast_source(group)
        if other is None:
            return
        other_server = MulticastServer(group, port, 0, 1, host=other)
        self.addCleanup(other_server.mc_server_sock.close)
        other_server.mc_server_sock.sendto(b"from-other", (group, port))
        self.assertIsNone(recv_once(listener.mc_client_sock, 0.4))

    @unittest.skipUnless(UNIX_PINNING, "uses linux or macOS multicast delivery")
    def test_multicast_without_bind_still_receives(self):
        # Default multicast egress is the primary interface, not loopback.
        # A listener that did not pass --bind must still receive that traffic.
        group = "239.255.1.6"
        listener = MulticastListener(group, 0)
        self.addCleanup(listener.mc_client_sock.close)
        port = listener.mc_client_sock.getsockname()[1]
        server = MulticastServer(group, port, 0, 1)
        self.addCleanup(server.mc_server_sock.close)
        server.mc_server_sock.sendto(b"open", (group, port))
        got = recv_once(listener.mc_client_sock, 1.0)
        self.assertIsNotNone(got)
        self.assertEqual(got[0], b"open")

    @unittest.skipUnless(UNIX_PINNING, "receivers are pinned on linux and macOS")
    def test_bound_receivers_use_wildcard_address(self):
        # A unicast bind drops limited broadcasts and group traffic, so a
        # bound receiver must stay on 0.0.0.0 and be pinned to the device.
        bc = BroadcastListener(0, host="127.0.0.1")
        self.addCleanup(bc.bc_client_sock.close)
        self.assertEqual(bc.bc_client_sock.getsockname()[0], "0.0.0.0")
        mc = MulticastListener("239.255.1.7", 0, host="127.0.0.1")
        self.addCleanup(mc.mc_client_sock.close)
        self.assertEqual(mc.mc_client_sock.getsockname()[0], "0.0.0.0")
        if MACOS:
            index = socket.if_nametoindex(LOOPBACK)
            for sock in (bc.bc_client_sock, mc.mc_client_sock):
                self.assertEqual(
                    sock.getsockopt(socket.IPPROTO_IP, _IP_BOUND_IF), index
                )

    @unittest.skipUnless(MACOS, "macOS broadcast delivery on a real interface")
    def test_macos_bound_broadcast_is_received(self):
        # lo0 cannot send limited broadcasts on macOS, so use a real interface.
        source = self._other_broadcast_source()
        if source is None:
            self.skipTest("no interface can send a limited broadcast")
        listener = BroadcastListener(0, host=source)
        self.addCleanup(listener.bc_client_sock.close)
        port = listener.bc_client_sock.getsockname()[1]
        server = BroadcastServer(port, 0, 1, host=source)
        self.addCleanup(server.bc_server_sock.close)
        self.assertEqual(server.bc_server_sock.getsockname()[0], source)
        server.bc_server_sock.sendto(b"bound", ("255.255.255.255", port))
        got = recv_once(listener.bc_client_sock, 1.0)
        self.assertIsNotNone(got)
        self.assertEqual(got[0], b"bound")
        self.assertEqual(got[1][0], source)

    def _other_broadcast_source(self):
        """An address other than loopback that can emit a limited broadcast."""
        for _name, ip in ipv4_interfaces():
            if ip == "127.0.0.1":
                continue
            probe = BroadcastListener(0)
            self.addCleanup(probe.bc_client_sock.close)
            port = probe.bc_client_sock.getsockname()[1]
            try:
                send_broadcast(ip, port, b"probe")
            except OSError:
                continue
            if recv_once(probe.bc_client_sock, 0.4) is not None:
                return ip
        return None

    def _other_multicast_source(self, group):
        """An address other than loopback that can emit local multicast."""
        for _name, ip in ipv4_interfaces():
            if ip == "127.0.0.1":
                continue
            probe = MulticastListener(group, 0)
            self.addCleanup(probe.mc_client_sock.close)
            port = probe.mc_client_sock.getsockname()[1]
            try:
                server = MulticastServer(group, port, 0, 1, host=ip)
            except ServiceExit:
                continue
            self.addCleanup(server.mc_server_sock.close)
            try:
                server.mc_server_sock.sendto(b"probe", (group, port))
            except OSError:
                continue
            if recv_once(probe.mc_client_sock, 0.4) is not None:
                return ip
        return None


if __name__ == "__main__":
    unittest.main()
