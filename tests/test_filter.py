# -*- coding: utf-8 -*-
"""Listeners drop packets meant for the other mode or another interface."""

import unittest

from bcmc.broadcast import BroadcastListener
from bcmc.multicast import MulticastListener


class FilterTests(unittest.TestCase):
    def setUp(self):
        self.bc = BroadcastListener(0)
        self.addCleanup(self.bc.bc_client_sock.close)
        self.mc = MulticastListener("239.255.1.3", 0)
        self.addCleanup(self.mc.mc_client_sock.close)

    def test_broadcast_listener_drops_multicast(self):
        self.assertFalse(self.bc.accepts(None, "239.255.1.3"))
        self.assertTrue(self.bc.accepts(None, "255.255.255.255"))
        self.assertTrue(self.bc.accepts(None, "192.168.1.255"))

    def test_multicast_listener_drops_other_destinations(self):
        self.assertFalse(self.mc.accepts(None, "255.255.255.255"))
        self.assertFalse(self.mc.accepts(None, "239.255.1.4"))
        self.assertTrue(self.mc.accepts(None, "239.255.1.3"))

    def test_bound_listeners_drop_other_interfaces(self):
        for listener in (self.bc, self.mc):
            listener.interface_index = 7
            dest = "239.255.1.3" if listener is self.mc else "255.255.255.255"
            self.assertTrue(listener.accepts(7, dest))
            self.assertFalse(listener.accepts(8, dest))

    def test_missing_packet_info_is_accepted(self):
        self.bc.interface_index = 7
        self.assertTrue(self.bc.accepts(None, None))
        self.assertTrue(self.mc.accepts(None, None))


if __name__ == "__main__":
    unittest.main()
