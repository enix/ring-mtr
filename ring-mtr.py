#!/usr/bin/env python
# coding: utf-8
from argparse import ArgumentParser, RawTextHelpFormatter
import sys
import logging
from signal import signal, SIGTERM

import os
import random
import dns.resolver
from pssh.clients import ParallelSSHClient


logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ENVVAR_PREFIX = "RING_MTR_"


def terminate(*_):  # pylint: disable=missing-function-docstring
    logger.info("Received SIGTERM, exiting.")
    sys.exit(0)


def main():  # pylint: disable=missing-function-docstring
    signal(SIGTERM, terminate)

    parser = ArgumentParser(
        description="Perform a MTR towards and from a subset of NLNOG ring nodes",
        formatter_class=RawTextHelpFormatter,
    )

    parser.add_argument(
        "-u",
        "--user",
        default=os.environ.get(ENVVAR_PREFIX + "USER"),
        help="SSH user.\nRequired, can be set using the env var "
        + ENVVAR_PREFIX
        + "USER",
    )

    parser.add_argument(
        "-r",
        "--root",
        default=os.environ.get(ENVVAR_PREFIX + "ROOT"),
        help="Ring node to/from which all MTRs will be performed.\nRequired, can be set using the env var "
        + ENVVAR_PREFIX
        + "ROOT",
    )

    parser.add_argument(
        "-n",
        "--number",
        default=os.environ.get(ENVVAR_PREFIX + "NUMBER", 10),
        type=int,
        help="Number of ring nodes to randomly select (can be 0).\nDefaults to 10, can be set using the env var "
        + ENVVAR_PREFIX
        + "NUMBER",
    )

    parser.add_argument(
        "-f",
        "--force",
        nargs="*",
        help="Force some nodes (short hostnames) to be present in the list if they have not been selected already.\n"
        + "Can be set using the env var "
        + ENVVAR_PREFIX
        + "FORCE , in a comma-separated list.",
    )

    parser.add_argument(
        "-c",
        "--cycles",
        default=os.environ.get(ENVVAR_PREFIX + "CYCLES", 10),
        type=int,
        help="MTR report cycles.\nDefaults to 10, can be set using the env var "
        + ENVVAR_PREFIX
        + "CYCLES",
    )

    parser.add_argument(
        "--connect-timeout",
        default=os.environ.get(ENVVAR_PREFIX + "CONNECT_TIMEOUT", 30),
        type=int,
        help="Timeout, in seconds, when connecting to the nodes.\nDefaults to 30, can be set using the env var "
        + ENVVAR_PREFIX
        + "CONNECT_TIMEOUT",
    )

    parser.add_argument(
        "-4",
        "--ipv4",
        action="store_true",
        help="Force IPv4 MTRs. Mutually exclusive with --ipv6\nDefault to false, can be set by setting the env var "
        + ENVVAR_PREFIX
        + "FORCE_IPV4 to 'true'",
    )

    parser.add_argument(
        "-6",
        "--ipv6",
        action="store_true",
        help="Force IPv6 MTRs. Mutually exclusive with --ipv4\nDefault to false, can be set by setting the env var "
        + ENVVAR_PREFIX
        + "FORCE_IPV6 to 'true'",
    )

    parser.add_argument(
        "--retries",
        default=os.environ.get(ENVVAR_PREFIX + "CONNECT_RETRIES", 1),
        type=int,
        help="Number of retries when connecting to the nodes.\nDefaults to 1, can be set using the env var "
        + ENVVAR_PREFIX
        + "CONNECT_RETRIES",
    )

    args = parser.parse_args()

    # Check user is present
    if args.user is None:
        parser.print_usage(sys.stderr)
        print(
            f"{os.path.basename(__file__)}: error: argument --user (or env var {ENVVAR_PREFIX}USER) is mandatory."
        )
        sys.exit(1)

    # Check root is present
    if args.root is None:
        parser.print_usage(sys.stderr)
        print(
            f"{os.path.basename(__file__)}: error: argument --root (or env var {ENVVAR_PREFIX}ROOT) is mandatory."
        )
        sys.exit(1)

    # Manually get the forced nodes list from env var if needed, or set an empty list as default
    if args.force is None:
        envvar = os.environ.get(ENVVAR_PREFIX + "FORCE")
        if envvar is None:
            args.force = []
        else:
            args.force = envvar.split(",")

    # Check if v4 or v6 was forced
    if not args.ipv4:
        if os.environ.get(ENVVAR_PREFIX + "FORCE_IPV4", "") == "true":
            args.ipv4 = True
    if not args.ipv6:
        if os.environ.get(ENVVAR_PREFIX + "FORCE_IPV6", "") == "true":
            args.ipv6 = True
    if args.ipv4 and args.ipv6:
        parser.print_usage(sys.stderr)
        print(
            f"{os.path.basename(__file__)}: error: cannot force both IPv4 and IPv6 simultaneously."
        )
        sys.exit(1)
    elif args.ipv4:
        mtr_ip_version_flag = "-4"
    elif args.ipv6:
        mtr_ip_version_flag = "-6"
    else:
        mtr_ip_version_flag = ""

    # Get all current ring nodes from DNS
    answers = dns.resolver.resolve("ring.nlnog.net", "TXT")
    nodes = " ".join([str(i).strip('"') for i in answers]).split()
    # 'nodes' will be shaped, so we keep an unaltered list of all ring nodes
    all_nodes = nodes.copy()

    # Remove root node from the list (and check it is a valid ring node)
    try:
        nodes.remove(args.root)
    except ValueError as exc:
        raise ValueError(
            f"The selected root, {args.root} is not a known ring node."
        ) from exc

    # Select a subset
    nodes = random.sample(nodes, args.number)

    # Manually add a forced subset (and check they are valid nodes) :
    all_nodes_are_valid = True
    invalid_nodes = []
    for forced_node in args.force:
        if forced_node not in all_nodes:
            all_nodes_are_valid = False
            invalid_nodes.append(forced_node)
        elif forced_node not in nodes:  # Add if not already present, or do nothing
            nodes.append(forced_node)

    if not all_nodes_are_valid:
        raise ValueError(f"Forced nodes {invalid_nodes} are not known ring nodes.")

    # Let's go

    logger.info(
        (
            "Performing bidirectionnal MTRs %s with %s cycles between '%s' and the following nodes : %s "
            "using user '%s', %ss of connect timeout and %s connect retries."
        ),
        mtr_ip_version_flag,
        args.cycles,
        args.root,
        nodes,
        args.user,
        args.connect_timeout,
        args.retries,
    )

    # Add the DNS suffix
    nodes = [n + ".ring.nlnog.net" for n in nodes]

    # "Inbound" are the MTRs from each of the remote node towards the root node,
    # and "outbound" are the MTRs from the root node towards each of the remote nodes

    # Run one MTR on each remote node towards our root node
    inbound_client = ParallelSSHClient(
        nodes, user=args.user, timeout=args.connect_timeout, num_retries=args.retries
    )
    inbound_output = inbound_client.run_command(
        f"mtr {mtr_ip_version_flag} -c {args.cycles} -w -z -b {args.root}.ring.nlnog.net",
        stop_on_errors=False,
    )

    # Run multiple MTRs on our root node towards each of the remote node
    outbound_client = ParallelSSHClient(
        [args.root + ".ring.nlnog.net"] * len(nodes),
        user=args.user,
        pool_size=20,  # Limit the concurrent connections, since they are all on the same host
        timeout=args.connect_timeout,
        num_retries=args.retries,
    )
    outbound_output = outbound_client.run_command(
        f"mtr {mtr_ip_version_flag} -c {args.cycles} -w -z -b %s",
        host_args=nodes,
        stop_on_errors=False,
    )

    # Wait for all remote commands to terminate
    inbound_client.join()
    outbound_client.join()

    # Index the results per remote node (source for "inbound" MTRs, and target for "outbound" MTRs)
    inbound_results = {o.host: o for o in inbound_output}
    # The following relies on a consistent list order
    outbound_results = {nodes[outbound_output.index(o)]: o for o in outbound_output}

    # This thing is a big old printer

    print()
    for host, inbound_host_output in inbound_results.items():
        outbound_host_output = outbound_results[host]
        print("-------------------------")
        print("Node: " + host)
        print("")

        # Print information related to MTR from the remote node to the root node (inbound)

        print(f"MTR inbound : from {host} to {args.root}.ring.nlnog.net :")
        print("")
        inbound_stdout = inbound_host_output.stdout
        if inbound_host_output.exception is not None:
            print("    Encountered an error for inbound MTR:")
            print("    " + str(inbound_host_output.exception))
            inbound_stdout = []  # This would be None, which is not iterable
        for line in inbound_stdout:
            print("   " + line)
        if inbound_host_output.exit_code:
            print("")
            print("----")
            print("    Exit code was: " + str(inbound_host_output.exit_code))
            print("    StdErr:")
            for line in inbound_host_output.stderr:
                print("   " + line)
            print("----")
        print("")

        # Print information related to MTR from the root node to the remote node (outbound)

        print(f"MTR outbound : from {args.root}.ring.nlnog.net to {host} :")
        print("")
        outbound_stdout = outbound_host_output.stdout
        if outbound_host_output.exception is not None:
            print("    Encountered an error for outbound MTR :")
            print("    " + str(outbound_host_output.exception))
            outbound_stdout = []  # This would be None, which is not iterable
        for line in outbound_stdout:
            print("   " + line)
        if outbound_host_output.exit_code:
            print("")
            print("----")
            print("    Exit code was: " + str(outbound_host_output.exit_code))
            print("    StdErr:")
            for line in outbound_host_output.stderr:
                print("   " + line)
            print("----")
        print("")


if __name__ == "__main__":
    main()
