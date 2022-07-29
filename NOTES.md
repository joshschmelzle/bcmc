# bcmc development notes

## IP_TOS and Windows

It appears setting IP_TOS on Windows 10 and 11 does not work anymore. Several searches have also indicated this is broke for iperf3 -S options.

The Microsoft docs indicate do not use IP_TOS and use their QoS API instead. Writing a wrapper for that is likely out of scope for this project.

<https://docs.microsoft.com/en-us/windows/win32/winsock/ipproto-ip-socket-options>.
