from botocore.exceptions import ClientError

from .abstract import AbstractWrapper


class EC2Wrapper(AbstractWrapper):
    name = "ec2"
    endpoint_url = "https://api.cloud.croc.ru:443"

    def get_all_instances(self):
        return list(self.resource.instances.all())

    def get_instances_by_tags(self, *tags: str):
        return self.resource.instances.filter(
            Filters=[{"Name": "tag:Name", "Values": tags}]
        )

    def get_instance(self, idn: str):
        """
        :param idn: The ID of the launch instance.
        """
        return self.resource.Instance(idn)

    def start_instance(self, idn: str):
        """
        :param idn: The ID of the launch instance.
        """
        self.log_info("Starting instance %s...", idn)
        i = self.get_instance(idn)
        try:
            i.start()
            i.wait_until_running()
            self.log_info("Instance %s started", idn)
        except ClientError as err:
            self.log_error(
                "Couldn't start instance %s. Here's why: %s: %s",
                idn,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )

    def stop_instance(self, idn: str):
        """
        :param idn: The ID of the launch instance.
        """
        self.log_info("Stopping instance %s...", idn)
        i = self.get_instance(idn)
        try:
            i.stop()
            i.wait_until_stopped()
            self.log_info("Instance %s stopped", idn)
        except ClientError as err:
            self.log_error(
                "Couldn't stop instance %s. Here's why: %s: %s",
                idn,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )

    def terminate_instance(self, idn: str):
        """
        :param idn: The ID of the launch instance.
        """
        self.log_info("Terminating instance %s...", idn)
        i = self.get_instance(idn)
        try:
            i.terminate()
            i.wait_until_terminated()
            self.log_info("Instance %s terminated", idn)
        except ClientError as err:
            self.log_error(
                "Couldn't terminate instance %s. Here's why: %s: %s",
                idn,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )

    def run_instance_from_template(
        self,
        *,
        idn: str | None = None,
        name: str | None = None,
        version: str | None = None,
        subnet: str,
        tag_value: str,
        min_count: int = 1,
        max_count: int = 1,
    ):
        """
        :param idn: The ID of the launch template.
            You must specify the idn or the name, but not both.
        :param name: The name of the launch template.
            You must specify the name or the idn, but not both.
        :param version: The launch template version number, $Latest,
            or $Default .
            If the value is $Latest, Amazon EC2 uses the latest version
            of the launch template.
            If the value is $Default, Amazon EC2 uses the default version
            of the launch template.
            Default: The default version of the launch template.
        :param subnet: The ID of the subnet to launch the instance into.
            If you specify a network interface, you must specify any subnets
            as part of the network interface.
        :param tag_value: tag to assign to instance.
        :param min_count: The minimum number of instances to launch.
            Default: 1
        :param max_count: The maximum number of instances to launch.
            Default: 1
        """
        # check and prepare arguments
        if bool(idn) == bool(name):
            raise ValueError(
                "You must specify the idn or the name, but not both."
            )
        launch_template = dict()
        if idn is not None:
            launch_template["LaunchTemplateId"] = idn
        if name is not None:
            launch_template["LaunchTemplateName"] = name
        if version is not None:
            launch_template["Version"] = version
        # create an instance
        try:
            self.log_info(
                "Creation of instance from template %s...", idn or name
            )
            instances = self.resource.create_instances(
                LaunchTemplate=launch_template,
                SubnetId=subnet,
                TagSpecifications=[
                    {
                        "ResourceType": "instance",
                        "Tags": [{"Key": "Name", "Value": tag_value}],
                    }
                ],
                MinCount=min_count,
                MaxCount=max_count,
            )
            i = instances[0]
            self.log_info(
                "Instance info: "
                "Id: %s, state: %s, private ip: %s, public ip: %s",
                i.id,
                i.state,
                i.private_ip_address,
                i.public_ip_address,
            )
            self.log_info("Waiting until exists")
            i.wait_until_exists()
            self.log_info("Waiting until running")
            i.wait_until_running()
            self.log_info("Instance created in run")
            return i
        # handle errors
        except ClientError as err:
            self.log_error(
                "Couldn't create instance from template %s. "
                "Here's why: %s: %s",
                idn or name,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise


def main():
    import logging

    logging.basicConfig(level=logging.INFO)

    ec2 = EC2Wrapper.from_resource()
    # ins = ec2.get_instances_by_tags("cpu bound")
    ins = ec2.get_all_instances()
    for i in ins:
        print(
            i.id,
            i.state,
            i.private_ip_address,
            i.public_ip_address,
        )

    # ec2.run_instance_from_template(
    #     # idn="lt-916D85F3",
    #     name="cpu_bound",
    #     # version="1",
    #     subnet="subnet-68302D82",
    # )
    #
    # i-427B1EC2 - load balancer
    # i-7C537E42 - cpu bound
    # ec2.start_instance("i-427B1EC2")
    # ec2.terminate_instance("i-D061ECA2")
    # i = ec2.get_instance("i-D061ECA2")
    # print(
    #     i.id,
    #     i.state,
    #     i.private_ip_address,
    #     i.public_ip_address,
    # )


if __name__ == "__main__":
    main()
