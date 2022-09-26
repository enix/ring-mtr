# NLNOG Ring bi-directional MTR

[![License MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Brought by Enix](https://img.shields.io/badge/Brought%20to%20you%20by-ENIX-%23377dff?labelColor=888&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAQAAAC1QeVaAAAABGdBTUEAALGPC/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAAmJLR0QA/4ePzL8AAAAHdElNRQfkBAkQIg/iouK/AAABZ0lEQVQY0yXBPU8TYQDA8f/zcu1RSDltKliD0BKNECYZmpjgIAOLiYtubn4EJxI/AImzg3E1+AGcYDIMJA7lxQQQQRAiSSFG2l457+655x4Gfz8B45zwipWJ8rPCQ0g3+p9Pj+AlHxHjnLHAbvPW2+GmLoBN+9/+vNlfGeU2Auokd8Y+VeYk/zk6O2fP9fcO8hGpN/TUbxpiUhJiEorTgy+6hUlU5N1flK+9oIJHiKNCkb5wMyOFw3V9o+zN69o0Exg6ePh4/GKr6s0H72Tc67YsdXbZ5gENNjmigaXbMj0tzEWrZNtqigva5NxjhFP6Wfw1N1pjqpFaZQ7FAY6An6zxTzHs0BGqY/NQSnxSBD6WkDRTf3O0wG2Ztl/7jaQEnGNxZMdy2yET/B2xfGlDagQE1OgRRvL93UOHqhLnesPKqJ4NxLLn2unJgVka/HBpbiIARlHFq1n/cWlMZMne1ZfyD5M/Aa4BiyGSwP4Jl3UAAAAldEVYdGRhdGU6Y3JlYXRlADIwMjAtMDQtMDlUMTQ6MzQ6MTUrMDI6MDDBq8/nAAAAJXRFWHRkYXRlOm1vZGlmeQAyMDIwLTA0LTA5VDE0OjM0OjE1KzAyOjAwsPZ3WwAAAABJRU5ErkJggg==)](https://enix.io)

A tool to automatically run My [Traceroute (MTR)](https://github.com/traviscross/mtr) instances between a subset of the [NLNOG Ring](https://ring.nlnog.net/) nodes and a single node called "root". MTRs are run in both directions : from the root as well as towards the root. This provides useful insights regarding issues (such as packet loss or increased latency) on the paths between the nodes.

The remote ("non-root") nodes can either be chosen at random from [the full list of nodes](https://ring.nlnog.net/participants/), manually selected using their short hostname (without `.ring.nlnog.net`) or a combination of both.

The root node must be specified using its short hostname, and is the node you want to check connectivity to/from. It is usually your node.

## Installation

You have to be a member of the NLNOG ring, and have the correct configuration in `.ssh/config`. If your SSH key is passphrase-protected (it should !), you must have a woring SSH agent.

Clone the repository, and either install the python dependencies using `pip install -r requirements.txt` or, if you do not want to mess with PIP or virtual environments, launch the software using Docker (see below).

## Usage

```
$ ./ring-mtr.py --help
usage: ring-mtr.py [-h] [-u USER] [-r ROOT] [-n NUMBER] [-f [FORCE ...]] [-c CYCLES] [--connect-timeout CONNECT_TIMEOUT] [-4] [-6] [--retries RETRIES]

Perform a MTR towards and from a subset of NLNOG ring nodes

options:
  -h, --help            show this help message and exit
  -u USER, --user USER  SSH user.
                        Required, can be set using the env var RING_MTR_USER
  -r ROOT, --root ROOT  Ring node to/from which all MTRs will be performed.
                        Required, can be set using the env var RING_MTR_ROOT
  -n NUMBER, --number NUMBER
                        Number of ring nodes to randomly select (can be 0).
                        Defaults to 10, can be set using the env var RING_MTR_NUMBER
  -f [FORCE ...], --force [FORCE ...]
                        Force some nodes (short hostnames) to be present in the list if they have not been selected already.
                        Can be set using the env var RING_MTR_FORCE , in a comma-separated list.
  -c CYCLES, --cycles CYCLES
                        MTR report cycles.
                        Defaults to 10, can be set using the env var RING_MTR_CYCLES
  --connect-timeout CONNECT_TIMEOUT
                        Timeout, in seconds, when connecting to the nodes.
                        Defaults to 30, can be set using the env var RING_MTR_CONNECT_TIMEOUT
  -4, --ipv4            Force IPv4 MTRs. Mutually exclusive with --ipv6
                        Default to false, can be set by setting the env var RING_MTR_FORCE_IPV4 to 'true'
  -6, --ipv6            Force IPv6 MTRs. Mutually exclusive with --ipv4
                        Default to false, can be set by setting the env var RING_MTR_FORCE_IPV6 to 'true'
  --retries RETRIES     Number of retries when connecting to the nodes.
                        Defaults to 1, can be set using the env var RING_MTR_CONNECT_RETRIES
```

### Using docker

Copy the file `ring-mtr.example.env` into `ring-mtr.env` and adapt the values, especially the username.

Then, run `docker compose run ring-mtr`. You can use a mix of environment variables and command-line flags.

After a code update, make sure to rebuild the docker image using `docker compose build`.