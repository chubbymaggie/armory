#!/usr/bin/python

from included.ModuleTemplate import ToolTemplate
from database.repositories import BaseDomainRepository, DomainRepository
import os
import json
import pdb
from included.utilities.color_display import display, display_error


class Module(ToolTemplate):

    name = "Aquatone Takeover"
    binary_name = "aquatone-takeover"

    def __init__(self, db):
        self.db = db
        self.Domain = DomainRepository(db, self.name)
        self.BaseDomain = BaseDomainRepository(db, self.name)

    def set_options(self):
        super(Module, self).set_options()

        self.options.add_argument(
            "-i",
            "--import_database",
            help="Import domains from database",
            action="store_true",
        )
        self.options.add_argument(
            "-r",
            "--rescan",
            help="Run aquatone on hosts that have already been processed.",
            action="store_true",
        )
        self.options.set_defaults(timeout=None)

    def get_targets(self, args):
        """
        This module is used to build out a target list and output file list, depending on the arguments. Should return a
        list in the format [(target, output), (target, output), etc, etc]
        """
        targets = []

        if args.import_database:
            if args.rescan:
                all_domains = self.BaseDomain.all(scope_type="passive")
            else:
                all_domains = self.BaseDomain.all(tool=self.name, scope_type="passive")
            for d in all_domains:
                # We need to find all of the http/https ports and create the json file.
                output_path = os.path.join(
                    self.base_config["PROJECT"]["base_path"], "output", "aquatone", d.domain
                )
                if not os.path.exists(output_path):
                    os.makedirs(output_path)

                hosts_j = {}
                hosts = []
                open_ports = []
                urls = []

                targets.append(d.domain)

                for s in d.subdomains:
                    name = s.domain

                    for ip in s.ip_addresses:
                        hosts_j[name] = ip.ip_address
                        port_list = []
                        for p in ip.ports:

                            if "http" in p.service_name:
                                hosts.append("{}.{}".format(name, ip.ip_address))

                                port_list.append(p.port_number)
                                urls.append(
                                    "{}://{}:{}/".format(
                                        p.service_name, name, p.port_number
                                    )
                                )
                                urls.append(
                                    "{}://{}:{}/".format(
                                        p.service_name, ip.ip_address, p.port_number
                                    )
                                )
                        if port_list:
                            open_ports.append(
                                "{},{}".format(
                                    ip.ip_address, ",".join([str(o) for o in port_list])
                                )
                            )

                open(os.path.join(output_path, "hosts.txt"), "w").write(
                    "\n".join(list(set(hosts)))
                )
                open(os.path.join(output_path, "urls.txt"), "w").write(
                    "\n".join(list(set(urls)))
                )
                open(os.path.join(output_path, "open_ports.txt"), "w").write(
                    "\n".join(list(set(open_ports)))
                )
                open(os.path.join(output_path, "hosts.json"), "w").write(
                    json.dumps(hosts_j)
                )
        else:
            display_error("You need to supply domain(s).")

        res = []
        for t in targets:
            res.append({"target": t})

        return res

    def build_cmd(self, args):
        """
        Create the actual command that will be executed. Use {target} and {output} as placeholders.
        """
        cmd = self.binary + " -d {target} "

        if args.tool_args:
            cmd += args.tool_args

        return cmd

    def pre_run(self, args):
        output_path = os.path.join(self.base_config["PROJECT"]["base_path"], 'output')

        self.orig_home = os.environ["HOME"]

        os.environ["HOME"] = output_path

    def process_output(self, cmds):
        """
        Process the output generated by the earlier commands.
        """

    def post_run(self, args):

        display("Potential takeovers are stored in {}".format(os.environ["HOME"]))
        os.environ["HOME"] = self.orig_home
