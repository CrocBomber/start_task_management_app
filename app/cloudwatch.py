from .abstract import AbstractWrapper


class CloudWatchWrapper(AbstractWrapper):
    name = "cloudwatch"
    endpoint_url = "https://monitoring.cloud.croc.ru:443"

    def get_all_metrics(self):
        return list(self.resource.metrics.all())

    def get_all_alarms(self):
        return list(self.resource.alarms.all())

    def get_alarms_by_prefix(self, prefix: str):
        self.log_info(f"Get alarms by prefix {prefix}")
        alarms = self.resource.alarms.filter(
            AlarmNamePrefix=prefix,
        )
        alarms_list = list(alarms)
        self.log_info(f"We got {len(alarms_list)} alarms")
        return alarms_list

    def get_alarm_by_name(self, name: str):
        alarms = self.resource.alarms.filter(AlarmNames=[name])
        alarms = list(alarms)
        if alarms:
            return alarms[0]
        else:
            return None

    @staticmethod
    def _get_alarm_name(instance_id: str, name_prefix: str):
        return f"{name_prefix}{instance_id}"

    def get_alarms_by_instance_id(self, instance_id: str, prefix: str):
        name = self._get_alarm_name(instance_id, prefix)
        alarm = self.get_alarm_by_name(name)
        return alarm

    def create_cpu_utilization_alarm(
        self,
        *,
        instance_id: str,
        statistic: str,
        period: int,
        evaluation_periods: int,
        threshold: float,
        comparison_operator: str,
        name_prefix: str,
    ):
        """
        Creates or updates CPU Utilization alarm for specified instance.
        :param instance_id: The ID of the instance to associate with the alarm.
        :param statistic: The statistic for the metric specified in MetricName,
            other than percentile. For percentile statistics, use
            ExtendedStatistic. When you call PutMetricAlarm and specify a
            MetricName, you must specify either Statistic or ExtendedStatistic,
            but not both.
        :param period: The length, in seconds, used each time the metric
            specified in MetricName is evaluated. Valid values are 10, 30,
            and any multiple of 60.
        :param evaluation_periods: The number of periods over which data is
            compared to the specified threshold. If you are setting an alarm
            that requires that a number of consecutive data points be breaching
            to trigger the alarm, this value specifies that number. If you are
            setting an "M out of N" alarm, this value is the N.
            An alarm's total current evaluation period can be no longer than
            one day, so this number multiplied by Period cannot be more than
            86,400 seconds.
        :param threshold: The value against which the specified statistic is
            compared. This parameter is required for alarms based on static
            thresholds, but should not be used for alarms based on anomaly
            detection models.
        :param comparison_operator: The arithmetic operation to use when
            comparing the specified statistic and threshold. The specified
            statistic value is used as the first operand. The values
            LessThanLowerOrGreaterThanUpperThreshold, LessThanLowerThreshold,
            and GreaterThanUpperThreshold are used only for alarms based on
            anomaly detection models.
        :param name_prefix: The prefix that make an alarm's name via
            concatenating with instance id. Default: _cpu_utilization_alarm
        """
        metric = self.resource.Metric("AWS/EC2", "CPUUtilization")
        alarm_name = self._get_alarm_name(instance_id, name_prefix)
        metric.put_alarm(
            AlarmName=alarm_name,
            ActionsEnabled=False,
            Statistic=statistic,
            Period=period,
            EvaluationPeriods=evaluation_periods,
            Threshold=threshold,
            ComparisonOperator=comparison_operator,
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
        )

    def delete_alarm_for_instance(
        self,
        instance_id: str,
        name_prefix: str,
    ):
        name = self._get_alarm_name(instance_id, name_prefix)
        self.log_info(f"Delete alarm with name {name}")
        alarm = self.get_alarm_by_name(name)
        if alarm:
            alarm.delete()
            self.log_info(f"Alarm with name {name} deleted")
        else:
            self.log_warning(f"Alarm with name {name} not found")
