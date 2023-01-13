import logging
from dataclasses import dataclass

from .cloudwatch import CloudWatchWrapper
from .ec2 import EC2Wrapper
from .nginx import NginxConfig

logger = logging.getLogger(__name__)


@dataclass
class WatchDog:
    cw: CloudWatchWrapper
    ec2: EC2Wrapper
    nginx_config: NginxConfig
    subnet_id: str
    node_limit: int = 4
    watched_app_tag: str = "cpu bound"
    template_id: str | None = None
    template_name: str | None = "cpu_bound"
    template_version: str | None = None
    application_port: int = 5000
    alarm_name_prefix: str = "cpu_bound_cpu_utilization_"

    def create_new_node(self):
        instance = self.ec2.run_instance_from_template(
            idn=self.template_id,
            name=self.template_name,
            version=self.template_version,
            subnet=self.subnet_id,
            tag_value=self.watched_app_tag,
        )
        self.cw.create_cpu_utilization_alarm(
            instance=instance.id,
            statistic="Average",
            period=60,  # seconds
            evaluation_periods=1,  # times
            threshold=70.0,  # percent
            comparison_operator="GreaterThanThreshold",
            name_prefix=self.alarm_name_prefix,
        )
        # todo: delete it
        with self.nginx_config as nc:
            host = f"{instance.private_ip_address}:{self.application_port}"
            nc.add_upstream_host(host)

    def start_node(self, node_id):
        self.ec2.start_instance(node_id)

    def purge_node(self, idn: str):
        self.ec2.terminate_instance(idn)
        self.cw.delete_alarm_for_instance(idn, self.alarm_name_prefix)
        # todo: delete it
        i = self.ec2.get_instance(idn)
        with self.nginx_config as nc:
            host = f"{i.private_ip_address}:{self.application_port}"
            nc.add_upstream_host(host)

    def refill_nginx_upstream(self, instances: list):
        hosts = [
            f"{i.private_ip_address}:{self.application_port}"
            for i in instances
        ]
        with self.nginx_config as nc:
            nc.refill_upstream(*hosts)

    def get_instances(self):
        instances = self.ec2.get_instances_by_tags(self.watched_app_tag)
        running, stopped = [], []
        for i in instances:
            status = i.state["Name"]
            if status == "running":
                running.append(i)
            elif status == "stopped":
                stopped.append(i)
            else:
                logger.warning(
                    f"Instance {i.id} have ambiguous status {status}"
                )
        return running, stopped

    def check_alarms(self):
        """
        Iterates through CPU Utilization alarms and checks if all of them
        crossed the threshold.
        If it was happened and node limit wasn't reached,
        then runs a stopped node or creates a new one.
        If more than two nodes have CPU Utilization under the threshold, then
        stops other nodes.
        """
        running, stopped = self.get_instances()
        if not running:
            if not stopped:
                # if no instances found, then create one
                self.create_new_node()
            else:
                # if no running, bot stopped exists, then run one
                self.start_node(stopped[0].id)
            # acquire nodes again and refill nginx upstream and exit
            running, stopped = self.get_instances()
            self.refill_nginx_upstream(running)
            return
        # check alarms
        alarms = self.cw.get_alarms_by_prefix(self.alarm_name_prefix)
        a_count = 0
        for a in alarms:
            if a.state_value == "alarm":
                a_count += 1
        if a_count >= len(running):
            if not stopped:
                self.create_new_node()
            else:
                self.start_node(stopped[0].id)
        # acquire nodes again and refill nginx upstream and exit
        running, stopped = self.get_instances()
        self.refill_nginx_upstream(running)
        return


def main():
    logging.basicConfig(level=logging.INFO)
    cw = CloudWatchWrapper.from_resource()
    ec2 = EC2Wrapper.from_resource()
    nginx_config = NginxConfig(
        "/home/bomber/dev/croc/start_task/managment_app/nginx.conf"
    )
    wd = WatchDog(cw, ec2, nginx_config, subnet_id="subnet-68302D82")
    # wd.create_new_node()
    wd.purge_node("i-49C196E2")


if __name__ == "__main__":
    main()
