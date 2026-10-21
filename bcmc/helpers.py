# -*- coding: utf-8 -*-
#
# helpers.py: helper functions for bcmc

import platform
import socket
import struct


class ServiceExit(Exception):
    """
    Exception to trigger clean exit of running threads
    """


# SIOCGIFADDR differs by platform. Both return a struct ifreq whose
# sockaddr_in address sits at bytes 20..24.
_SIOCGIFADDR = {"Linux": 0x8915, "Darwin": 0xC0206921}

# Darwin IP_BOUND_IF (netinet/in.h). Python does not export it.
_IP_BOUND_IF = getattr(socket, "IP_BOUND_IF", 25)


def ipv4_interfaces():
    """Return [(interface name, IPv4 address), ...] for local interfaces.

    Supported on Linux and macOS. Empty elsewhere (Windows has no fcntl).
    """
    try:
        import fcntl
    except ImportError:
        return []
    request = _SIOCGIFADDR.get(platform.system())
    if request is None:
        return []
    try:
        names = [name for _, name in socket.if_nameindex()]
    except OSError:
        return []

    found = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for name in names:
            try:
                packed = struct.pack("256s", name.encode("ascii")[:15])
                info = fcntl.ioctl(sock.fileno(), request, packed)
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

    Linux and macOS do not deliver limited broadcasts, or multicast, to a UDP
    socket bound to a unicast address. Pinning selects the interface while
    the socket stays bound to the wildcard address so those packets arrive.
    Linux uses SO_BINDTODEVICE and macOS uses IP_BOUND_IF. Windows has
    neither.
    """
    name = interface_name_for_ipv4(address)
    if not name:
        return False
    system = platform.system()
    try:
        if system == "Linux" and hasattr(socket, "SO_BINDTODEVICE"):
            sock.setsockopt(
                socket.SOL_SOCKET, socket.SO_BINDTODEVICE, f"{name}\0".encode("ascii")
            )
            return True
        if system == "Darwin":
            sock.setsockopt(
                socket.IPPROTO_IP, _IP_BOUND_IF, socket.if_nametoindex(name)
            )
            return True
    except OSError:
        return False
    return False


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
