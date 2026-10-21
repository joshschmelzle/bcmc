# -*- coding: utf-8 -*-
#
# helpers.py: helper functions for bcmc

import os
import socket
import struct


class ServiceExit(Exception):
    """
    Exception to trigger clean exit of running threads
    """


# Linux SIOCGIFADDR. Other platforms fail the ioctl and yield no interfaces.
_SIOCGIFADDR = 0x8915


def ipv4_interfaces():
    """Return [(interface name, IPv4 address), ...] for local interfaces.

    Empty on platforms that cannot enumerate interfaces with this method.
    Windows has no fcntl, and non-Linux systems have no /sys/class/net.
    """
    try:
        import fcntl
    except ImportError:
        return []
    try:
        names = os.listdir("/sys/class/net")
    except OSError:
        return []

    found = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for name in names:
            try:
                packed = struct.pack("256s", name.encode("ascii")[:15])
                info = fcntl.ioctl(sock.fileno(), _SIOCGIFADDR, packed)
            except OSError:
                continue
            if not info or len(info) < 24:
                continue
            ip = socket.inet_ntoa(info[20:24])
            found.append((name, ip))
    finally:
        sock.close()
    return found


def interface_name_for_ipv4(address):
    """Return the interface that owns address, or None."""
    for name, ip in ipv4_interfaces():
        if ip == address:
            return name
    return None


def _announce(address):
    name = interface_name_for_ipv4(address)
    if name:
        print(f"Using bind address {address} ({name})")
    else:
        print(f"Using bind address {address}")


def _bind_or_die(sock, target):
    try:
        sock.bind(target)
    except OSError as exc:
        label = target[0] if target[0] else "0.0.0.0"
        print(f"Error: could not bind to {label}: {exc}")
        raise ServiceExit from exc


def _pin_socket_to_interface(sock, address):
    """Pin sock to the device that owns address. Return True on success.

    Linux does not deliver limited broadcasts, or multicast, to a UDP socket
    bound to a unicast address. SO_BINDTODEVICE selects the interface while
    the socket stays bound to the wildcard address so those packets arrive.
    The option is not present on Windows.
    """
    option = getattr(socket, "SO_BINDTODEVICE", None)
    if option is None:
        return False
    name = interface_name_for_ipv4(address)
    if not name:
        return False
    try:
        sock.setsockopt(socket.SOL_SOCKET, option, f"{name}\0".encode("ascii"))
    except OSError:
        return False
    return True


def bind_udp_sender(sock, address, multicast=False):
    """Select the source address and egress interface for a UDP sender.

    No effect when address is empty. Binding the socket makes the kernel use
    that address as the packet source, which is what picks the broadcast
    interface. Multicast egress is selected with IP_MULTICAST_IF; that option
    is also what server ``--debug`` output prints.
    """
    if not address:
        return
    _announce(address)
    try:
        sock.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(address)
        )
    except OSError as exc:
        if multicast:
            print(f"Error: could not select multicast interface {address}: {exc}")
            raise ServiceExit from exc
    _bind_or_die(sock, (address, 0))


def bind_udp_receiver(sock, address, port, multicast=False):
    """Bind a UDP receiver, restricted to address when one was requested.

    Multicast sockets are never bound to the unicast address: on Linux that
    drops group traffic. They bind to the wildcard port and, when possible,
    are pinned to the device. Membership is applied by the caller.
    """
    port = int(port)
    if not address:
        sock.bind(("", port))
        return
    _announce(address)
    pinned = _pin_socket_to_interface(sock, address)
    if pinned or multicast:
        _bind_or_die(sock, ("", port))
        if not pinned:
            print(
                f"Warning: {address} is not pinned to a device and may "
                "receive on other interfaces"
            )
        return
    _bind_or_die(sock, (address, port))
