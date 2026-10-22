```text
 _
| |__   ___ _ __ ___   ___   _ __  _   _
| '_ \ / __| '_ ` _ \ / __| | '_ \| | | |
| |_) | (__| | | | | | (__ _| |_) | |_| |
|_.__/ \___|_| |_| |_|\___(_) .__/ \__, |
                            |_|    |___/
```

`bcmc` is a CLI-centric IP broadcast and multicast tool built with Python. It is a testing tool for generating and validating broadcast or multicast traffic.

`bcmc` can be run as a server to generate broadcast or multicast traffic, or as a client to receive it. It is a CLI-based client/server tool inspired by iperf.

`bcmc` is developed by Josh Schmelzle and Kevin L. Marshall and is released under a three-clause BSD license.

## installation

`bcmc` requires Python 3.13 or newer. Install it from [PyPI](https://pypi.org/project/bcmc/) with [pipx](https://pipx.pypa.io/) or pip:

```bash
pipx install bcmc
# or
python -m pip install bcmc
```

Check the installed version:

```bash
bcmc --version
```

## why `bcmc`?

Existing tools such as Multicast Hammer are platform specific and may have unsupported system dependencies on modern OSes. `bcmc` aims to be a free cross-platform tool that can be used on Linux, macOS, and Windows. Some optional features may not work on every OS; see troubleshooting below.

## usage

`bcmc` is a client/server tool which functions similar to iperf. It can be used to test and validate broadcast or multicast on 802.11 or 802.3 networks.

* You will need two hosts.
* Place both hosts on the target test network.
* Use one host to run `bcmc` in client mode (receive).
* Use the other host to run `bcmc` in server mode (transmit).

The server sends one packet per second (change it with `-i`) until you stop it with Ctrl+C.

### broadcast (-bc)

In broadcast mode, `bcmc` sends UDP packets to 255.255.255.255 on port 2002 by default.

```bash
bcmc -c -bc   # client (receive)
bcmc -s -bc   # server (transmit)
```

### multicast (-mc)

In multicast mode, `bcmc` sends UDP packets to the multicast group 239.0.0.2 on port 2002 by default. Use `--group` to pick another group and `--ttl` to set how many hops the packets may cross.

```bash
bcmc -c -mc   # client (receive)
bcmc -s -mc   # server (transmit)
```

## example output

Server sending multicast:

```text
$ bcmc -s -mc
Sending with socket: <socket.socket fd=3, family=2, type=2, proto=17, laddr=('0.0.0.0', 0)>
Sending multicast (73 bytes) -> multicast from sparkle.local to 239.0.0.2:2002 message 1 at 21:30:18.8077
Sending multicast (73 bytes) -> multicast from sparkle.local to 239.0.0.2:2002 message 2 at 21:30:19.8101
Sending multicast (73 bytes) -> multicast from sparkle.local to 239.0.0.2:2002 message 3 at 21:30:20.8112
^C
Stop requested ...
```

Client receiving it:

```text
$ bcmc -c -mc
Listening with socket: <socket.socket fd=3, family=2, type=2, proto=17, laddr=('0.0.0.0', 2002)>
Listening for multicasts on group 239.0.0.2 port 2002
-----------------------------------------------------
Receiving (73 bytes) time 21:30:18.8080 from 192.168.6.65:53032:
 -> multicast from sparkle.local to 239.0.0.2:2002 message 1 at 21:30:18.8077

Receiving (73 bytes) time 21:30:19.8106 from 192.168.6.65:53032:
 -> multicast from sparkle.local to 239.0.0.2:2002 message 2 at 21:30:19.8101

Receiving (73 bytes) time 21:30:20.8117 from 192.168.6.65:53032:
 -> multicast from sparkle.local to 239.0.0.2:2002 message 3 at 21:30:20.8112
^C
Stop requested ...
```

Each received message carries the sender's message number, so a gap in the numbers means a packet was lost.

## binding to an interface (-b)

On hosts with more than one network interface, use `-b` with the IPv4 address of the interface you want to test:

```bash
bcmc -s -mc -b 192.168.6.65   # send out of the interface that owns 192.168.6.65
bcmc -c -bc -b 192.168.6.65   # only show broadcasts that arrive on that interface
```

On Linux and macOS, a bound client only shows packets that arrived on that interface. Broadcast clients ignore multicast traffic and multicast clients ignore broadcasts, so several clients can run side by side on the same port.

## discovery tip

To try out `bcmc`, run it in two terminals on the same host:

* In one terminal, run `bcmc` in client mode.
* In the other, run `bcmc` in server mode.
* You should see the client print the incrementing messages sent by the server.

## troubleshooting

* **Nothing arrives at the client:** make sure the client host's firewall allows inbound UDP on the port you're using (2002 by default).
* **Windows server uses the wrong interface:** without `-b`, server mode on Windows sends from the interface with the lowest metric. Check the metrics with `route PRINT` in cmd.exe or PowerShell, or pass `-b` with the address of the interface you want.
* **Windows client shows traffic from every interface:** Python on Windows can't tell which interface a packet arrived on, so a bound Windows client can't filter by interface.
* **DSCP on Windows:** Windows ignores the `--dscp` value. See [NOTES.md](https://github.com/joshschmelzle/bcmc/blob/main/NOTES.md).
* **macOS multicast fails with "No route to host":** the host has no route for multicast. Use `-b` with an interface address, or add a route for 224.0.0.0/4.

## options

```text
usage: bcmc [-s|-c] [-bc|-mc] [options]
       bcmc [-h|--help] [-v|--version]

options:
  -h, --help          show this help message and exit
  -p, --port 2002     port to listen on/connect to
  -b, --bind <host>   bind to the interface associated with provided <host>
                      address (experimental)
  --debug             increase output for debugging purposes
  -c, --client        run in client mode
  -s, --server        run in server mode
  -bc, --broadcast    set traffic type to broadcast
  -mc, --multicast    set traffic type to multicast
  --group 239.0.0.2   multicast group address (239.0.0.2 by default)
  -i, --interval 1    seconds between packets sent in server mode
  --ttl 3             set the hop restriction in network for multicast server
  --dscp 46           set the Differentiated Service Code Point value applied
                      to packets sent in server mode
  --padding 0         number of additional null bytes per payload which is
                      sent in server mode
  --payload 'string'  add an arbitrary payload which is sent in server mode
```
