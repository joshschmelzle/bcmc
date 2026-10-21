# -*- coding: utf-8 -*-
"""Argument validation, padding, and idle CPU use."""

import contextlib
import io
import os
import signal
import subprocess
import sys
import time
import unittest

from bcmc.appsetup import setup_parser
from bcmc.broadcast import BroadcastServer
from bcmc.multicast import MulticastServer


def parse(argv):
    with contextlib.redirect_stderr(io.StringIO()):
        return setup_parser().parse_args(argv)


class ArgumentTests(unittest.TestCase):
    def test_bind_accepts_dotted_quad(self):
        self.assertEqual(parse(["-s", "-bc", "-b", "10.1.2.3"]).host, "10.1.2.3")

    def test_bind_rejects_malformed_addresses(self):
        for bad in ("1.2.3.4.5", "10.5", "10.0.5", "256.1.1.1", "a.b.c.d", "1..2.3"):
            with self.subTest(bad=bad), self.assertRaises(SystemExit):
                parse(["-s", "-bc", "-b", bad])

    def test_group_must_be_multicast(self):
        self.assertEqual(parse(["-c", "-mc", "--group", "239.1.2.3"]).group, "239.1.2.3")
        with self.assertRaises(SystemExit):
            parse(["-c", "-mc", "--group", "10.0.0.1"])

    def test_padding_must_be_non_negative_integer(self):
        self.assertEqual(parse(["-s", "-bc", "--padding", "5"]).padding, 5)
        for bad in ("-1", "x", "1.5"):
            with self.subTest(bad=bad), self.assertRaises(SystemExit):
                parse(["-s", "-bc", "--padding", bad])

    def test_server_help_text(self):
        text = setup_parser().format_help()
        self.assertIn("run in server mode", text)
        self.assertEqual(text.count("run in client mode"), 1)


class PaddingTests(unittest.TestCase):
    def test_broadcast_and_multicast_pad_with_the_same_null_bytes(self):
        bc = BroadcastServer(9, 5, 1)
        self.addCleanup(bc.bc_server_sock.close)
        mc = MulticastServer("239.255.1.8", 9, 5, 1)
        self.addCleanup(mc.mc_server_sock.close)
        for server in (bc, mc):
            payload = server.build_payload("hello")
            self.assertEqual(payload, "hello" + "\0" * 5)

    def test_custom_payload_is_padded(self):
        bc = BroadcastServer(9, 3, 1, payload="abc")
        self.addCleanup(bc.bc_server_sock.close)
        self.assertEqual(bc.build_payload("ignored"), "abc\0\0\0")


@unittest.skipIf(sys.platform == "win32", "uses POSIX signals and ps")
class IdleCpuTests(unittest.TestCase):
    def test_client_does_not_spin_while_idle(self):
        proc = subprocess.Popen(
            [sys.executable, "-m", "bcmc", "-c", "-mc", "-p", "0"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.addCleanup(proc.kill)
        time.sleep(1.0)
        cpu_before = self._cpu_seconds(proc.pid)
        time.sleep(2.0)
        cpu_after = self._cpu_seconds(proc.pid)
        proc.send_signal(signal.SIGINT)
        self.assertEqual(proc.wait(timeout=5), 0)
        # A busy loop burns about 2 CPU seconds here; idle should be near 0.
        self.assertLess(cpu_after - cpu_before, 0.5)

    @staticmethod
    def _cpu_seconds(pid):
        out = subprocess.check_output(["ps", "-o", "time=", "-p", str(pid)], text=True)
        parts = out.strip().replace("-", ":").split(":")
        seconds = 0.0
        for part in parts:
            seconds = seconds * 60 + float(part)
        return seconds


if __name__ == "__main__":
    unittest.main()
