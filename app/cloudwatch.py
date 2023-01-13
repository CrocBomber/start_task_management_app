from .abstract import AbstractWrapper


class CloudWatchWrapper(AbstractWrapper):
    name = "cloudwatch"
    endpoint_url = "https://monitoring.cloud.croc.ru:443"

    def get_all_metrics(self):
        return list(self.resource.metrics.all())

    def get_all_alarms(self):
        return list(self.resource.alarms.all())

    def get_alarms_by_prefix(self, prefix: str):
        alarms = self.resource.alarms.filter(
            AlarmNamePrefix=prefix,
        )
        return list(alarms)

    @staticmethod
    def _get_alarm_name(instance: str, name_prefix: str):
        return f"{name_prefix}{instance}"

    def create_cpu_utilization_alarm(
        self,
        *,
        instance: str,
        statistic: str,
        period: int,
        evaluation_periods: int,
        threshold: float,
        comparison_operator: str,
        name_prefix: str,
    ):
        """
        Creates or updates CPU Utilization alarm for specified instance.
        :param instance: The ID of the instance to associate with the alarm.
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
        alarm_name = self._get_alarm_name(instance, name_prefix)
        metric.put_alarm(
            AlarmName=alarm_name,
            ActionsEnabled=False,
            Statistic=statistic,
            Period=period,
            EvaluationPeriods=evaluation_periods,
            Threshold=threshold,
            ComparisonOperator=comparison_operator,
            Dimensions=[{"Name": "InstanceId", "Value": instance}],
        )

    def delete_alarm_for_instance(
        self,
        instance: str,
        name_prefix: str,
    ):
        alarm_name = self._get_alarm_name(instance, name_prefix)
        a = self.resource.Alarm(alarm_name)
        a.delete()


def main():
    import logging

    logging.basicConfig(level=logging.INFO)
    cw = CloudWatchWrapper.from_resource()

    # for m in cw.get_metrics():
    #     print(m)
    #     print(dir(m))
    # print()

    # cw.create_cpu_utilization_alarm(
    #     instance="i-D061ECA2",
    #     statistic="Average",
    #     period=60,
    #     evaluation_periods=1,
    #     threshold=70.0,
    #     comparison_operator="GreaterThanThreshold",
    # )
    cw.delete_alarm("i-D061ECA2")

    for a in cw.get_alarms():
        print(a)
        print(dir(a))
        print(
            a.name,
            "\n",
            a.state_value,
            "\n",  # ok or alarm
            a.dimensions,
            "\n",
            a.evaluation_periods,
            "\n",
            a.period,
            "\n",
            a.threshold,
            "\n",
            a.unit,
            "\n",
            a.threshold_metric_id,
            "\n",
            a.statistic,
            "\n",
        )

    # for m in cloudwatch.metrics.filter(MetricName="CPUUtilization"):
    #     print(m)
    #     print(dir(m))
    #     print(m.dimensions)
    #     cpu_utilization = m.get_statistics(
    #         Dimensions=m.dimensions,
    #         # на сервере время по utc
    #         StartTime=datetime.utcnow() - timedelta(seconds=300),
    #         EndTime=datetime.utcnow(),
    #         Period=60,  # period should be 60 seconds or greater
    #         Statistics=["Average"],
    #         Unit="Percent",
    #     )
    #     for dp in cpu_utilization["Datapoints"]:
    #         print(dp)


if __name__ == "__main__":
    main()
