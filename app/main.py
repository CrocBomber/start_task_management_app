import argparse
import configparser
import logging
import os
import signal
import threading
import time
import urllib.error
import urllib.request

from .cloudwatch import CloudWatchWrapper
from .ec2 import EC2Wrapper
from .nginx import NginxConfig

logger = logging.getLogger("main")


class WatchDog:
    def __init__(
        self,
        cw: CloudWatchWrapper,
        ec2: EC2Wrapper,
        nginx_config: NginxConfig,
        subnet_id: str,
        node_limit: int = 4,
        watched_app_tag: str = "cpu bound",
        template_id: str | None = None,
        template_name: str | None = "cpu_bound",
        template_version: str | None = None,
        application_port: int = 5000,
        alarm_name_prefix: str = "cpu_bound_cpu_utilization_",
        check_period: int = 60,
        endpoint_timeout: int = 600,
    ):
        self.cw = cw
        self.ec2 = ec2
        self.nginx_config = nginx_config
        self.subnet_id = subnet_id
        self.node_limit = int(node_limit)
        self.watched_app_tag = watched_app_tag
        self.template_id = template_id
        self.template_name = template_name
        self.template_version = template_version
        self.application_port = int(application_port)
        self.alarm_name_prefix = alarm_name_prefix
        self.check_period = check_period
        self.endpoint_timeout = int(endpoint_timeout)

    def create_alarm(self, instance_id):
        self.cw.create_cpu_utilization_alarm(
            instance_id=instance_id,
            statistic="Average",
            period=60,  # seconds
            evaluation_periods=1,  # times
            threshold=70.0,  # percent
            comparison_operator="GreaterThanThreshold",
            name_prefix=self.alarm_name_prefix,
        )

    def create_new_node(self):
        logger.info("Creating new node")
        instance = self.ec2.run_instance_from_template(
            idn=self.template_id,
            name=self.template_name,
            version=self.template_version,
            subnet=self.subnet_id,
            tag_value=self.watched_app_tag,
        )
        self.create_alarm(instance.id)
        logger.info(f"Node {instance.id} created")
        return instance

    def start_node(self, idn):
        logger.info(f"Start node {idn}")
        self.ec2.start_instance(idn)
        alarm = self.cw.get_alarms_by_instance_id(idn, self.alarm_name_prefix)
        if not alarm:
            self.create_alarm(idn)
        logger.info(f"Node {idn} started")

    def purge_node(self, idn: str):
        logger.info(f"Purge node {idn}")
        self.ec2.terminate_instance(idn)
        self.cw.delete_alarm_for_instance(idn, self.alarm_name_prefix)

    def get_instance_host_port(self, instance):
        return f"{instance.private_ip_address}:{self.application_port}"

    def refill_nginx_upstream(self, instances: list):
        hosts = [self.get_instance_host_port(i) for i in instances]
        with self.nginx_config as nc:
            nc.refill_upstream(*hosts)

    def get_instances(self):
        """
        Retrieves all instances from the cloud by tag name.
        :return: a tuple with two lists: the first with running instances,
            the second with stopped instances.
        """
        logger.info(f"Retrieve instances by tag {self.watched_app_tag}")
        instances = self.ec2.get_instances_by_tags(self.watched_app_tag)
        instances = list(instances)
        logger.info(f"Retrieved {len(instances)} instances.")
        running, stopped = [], []
        for i in instances:
            status = i.state["Name"]
            if status == "running":
                running.append(i)
            elif status == "stopped":
                stopped.append(i)
            else:
                logger.warning(
                    f"Instance {i.id} have ambiguous status: {status}"
                )
        logger.info(
            f"There are {len(running)} running instances "
            f"and {len(stopped)} stopped instances."
        )
        return running, stopped

    def update_nginx_upstream(self):
        running, stopped = self.get_instances()
        self.refill_nginx_upstream(running)
        self.reload_nginx_config()

    def start_or_create(self, running, stopped):
        """
        If we have stopped node, we start one. Else, if we don't reach the
        node limis, we run new node.
        :param running: list of the running instances
        :param stopped: list of the stopped instances
        """
        instance = None
        if stopped:
            instance = stopped[0]
            self.start_node(instance.id)
        elif len(running) < self.node_limit:
            instance = self.create_new_node()
        if instance:
            host_port = self.get_instance_host_port(instance)
            start = time.time()
            while time.time() - start < self.endpoint_timeout:
                try:
                    url = f"http://{host_port}/info"
                    logger.info(f"Wait for answer from {url}")
                    urllib.request.urlopen(url, timeout=10)
                    self.update_nginx_upstream()
                    break
                except OSError as err:
                    logger.warning(
                        f"An error occurs: {err}. But we still wait.."
                    )
                    continue
            else:
                logger.error(
                    f"Endpoint still unavailable after "
                    f"{self.endpoint_timeout} seconds"
                )

    def stop_node(self, running):
        if running:
            node_to_stop = running[-1]
            self.ec2.stop_instance(node_to_stop.id)
            self.update_nginx_upstream()

    def check_alarms(self):
        """
        Iterates through CPU Utilization alarms and checks if all of them
        crossed the threshold.
        If it was happened and node limit wasn't reached,
        then runs a stopped node or creates a new one.
        If more than two nodes have CPU Utilization under the threshold, then
        stops other nodes.
        """
        logger.info("Start alarms checking.")
        running, stopped = self.get_instances()
        if not running:
            logger.info("There is no one node exists. Run one..")
            self.start_or_create(running, stopped)
            return
        # check alarms
        alarms = self.cw.get_alarms_by_prefix(self.alarm_name_prefix)
        overloaded = 0
        for a in alarms:
            if a.state_value == "alarm":
                overloaded += 1
        logger.info(
            f"We have {overloaded} alarms in state alarm "
            f"and {len(running)} running nodes."
        )
        if overloaded >= len(running):
            logger.info("So we need to start or create another one.")
            self.start_or_create(running, stopped)
            logger.info("Alarms checking complete.")
            return
        elif len(running) - overloaded > 1:
            logger.info("So we need to stop one.")
            self.stop_node(running)
            logger.info("Alarms checking complete.")
        else:
            logger.info(
                "We have enough number of nodes, no need to start or stop."
            )

    @staticmethod
    def reload_nginx_config():
        cmd = "sudo /usr/bin/systemctl reload nginx.service"
        exit_code = os.system(cmd)
        if exit_code != 0:
            logger.error(
                f"Command {cmd} returned not zero exit code: {exit_code}"
            )


def main():
    # configure logging
    logging.basicConfig(
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        level=logging.INFO,
    )
    # init args
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-mc",
        "--main-config",
        type=argparse.FileType(),
        help="Main config",
    )
    parser.add_argument(
        "-cc",
        "--cloud-config",
        type=argparse.FileType(),
        help="Cloud config file with cloud credentials",
    )
    parser.add_argument(
        "-nc",
        "--nginx-config",
        type=argparse.FileType("r+"),
        help="Path to nginx config file",
    )
    args = parser.parse_args()
    # main config
    main_config = {}
    if args.main_config:
        logger.info(f"Read main config from file {args.main_config.name}")
        config = configparser.ConfigParser()
        config.read_file(args.main_config)
        if "default" in config:
            main_config = config["default"]
    # parse cloud config
    cloud_config = {}
    if args.cloud_config:
        logger.info(f"Read cloud config from file {args.cloud_config.name}")
        config = configparser.ConfigParser()
        config.read_file(args.cloud_config)
        if "default" in config:
            cloud_config = config["default"]
    # configure main class
    cw = CloudWatchWrapper.from_resource(**cloud_config)
    ec2 = EC2Wrapper.from_resource(**cloud_config)
    nginx_config = NginxConfig(args.nginx_config)
    wd = WatchDog(cw, ec2, nginx_config, **main_config)
    # configure stop handlers
    is_alive = True
    event = threading.Event()

    def handle(signal_number, _stack_frame):
        name = signal.Signals(signal_number).name
        logger.info(f"Catch signal: {name}")
        nonlocal is_alive
        is_alive = False
        event.set()

    for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(s, handle)
    # run main process
    while is_alive:
        wd.check_alarms()
        event.wait(wd.check_period)


if __name__ == "__main__":
    main()
