```text
 _
| |__   ___ _ __ ___   ___   _ __  _   _
| '_ \ / __| '_ ` _ \ / __| | '_ \| | | |
| |_) | (__| | | | | | (__ _| |_) | |_| |
|_.__/ \___|_| |_| |_|\___(_) .__/ \__, |
                            |_|    |___/
```

`bcmc` is a CLI-centric IP broadcast and multicast tool built with Python. it is a testing tool for generating and validating broadcast or multicast traffic.

`bcmc` can be run as a server to generate broadcast or multicast traffic or `bcmc` can be run as a client to receive broadcast or multicast traffic. it is a CLI-based client/server tool inspired by iperf.

`bcmc` is developed by Josh Schmelzle and Kevin L. Marshall and is released under a three-clause BSD license.

## why `bcmc`?

Existing tools such as Multicast Hammer are platform specific and may have unsupported system dependencies on modern OSes. `bcmc` aims to be a free cross-platform tool that can be used from *unix or Windows. While `bcmc` aims to function cross-platform, please note some optional features may not work on certain OSes.

## usage

`bcmc` is a client/server tool which functions similar to iperf. `bcmc` can be used to test and validate broadcast or multicast on 802.11 or 802.3 networks.

steps:

* You will need two hosts
* Place both hosts on the target test network
* Use one host to run `bcmc` in client mode (receive)
* Use the other host to run `bcmc` in server mode (transmit)

## broadcast traffic

In broadcast mode, the default behavior for `bcmc` is to send IP layer UDP packets to 255.255.255.255.

## multicast traffic

In multicast mode, the default behavior for `bcmc` is to send IP layer UDP packets to 239.0.0.2 as the multicast group address.

## modes (-s|-c)

`bcmc` can be run as client or server.

## traffic (-bc|-mc)

`bcmc` can generate broadcast or multicast IP packets.

## broadcast (-bc)

client usage:

```bash
bcmc -c -bc
```

server usage:

```bash
bcmc -s -bc
```

## multicast (-mc)

client usage:

```bash
bcmc -c -mc
```

server usage:

```bash
bcmc -s -mc
```

## discovery tip

* to understand or "try out" the behavior of `bcmc`, you can also use `bcmc` with two different terminals on the same host.
* in one terminal, run `bcmc` in client mode
* in the other, run `bcmc` in server mode
* you should see incrementing messages from `bcmc` running in server mode in the terminal running `bcmc` as client mode.

## troubleshooting

On Windows, `bcmc` server (`-s`) mode will default to the interface with the lowest metric. If you are having issues where client (`-c`) mode is not receiving messages from server (`-s`) mode, investigate the metric by running `route PRINT` from conhost (cmd.exe) or PowerShell.

## optional arguments

```bash
usage: bcmc [-s|-c] [-bc|-mc] [options]
       bcmc [-h|--help] [-v|--version]

options:
  -h, --help            show this help message and exit
  -p 2002, --port 2002  port to listen on/connect to
  -b <host>, --bind <host>
                        bind to the interface associated with provided <host> address (experimental)
  --debug               increase output for debugging purposes
  -c, --client          run in client mode
  -s, --server          run in client mode
  -bc, --broadcast      set traffic type to broadcast
  -mc, --multicast      set traffic type to multicast
  --group 239.0.0.2     multicast group address (239.0.0.2 by default)
  -i 1, --interval 1    interval to send multicast packets
  --ttl 3               set the hop restriction in network for multicast server
  --dscp 46             set the Differentiated Service Code Point value applied to packets sent in server mode
  --padding 0           number of additional null bytes per payload which is sent in server mode
  --payload 'string'    add an arbitrary payload which is sent in server mode
```
