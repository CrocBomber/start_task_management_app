import logging
from abc import ABC, abstractmethod

import boto3


class AbstractWrapper(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def endpoint_url(self) -> str:
        ...

    @classmethod
    def from_resource(cls, *args, **kwargs):
        if "endpoint_url" not in kwargs:
            kwargs["endpoint_url"] = cls.endpoint_url
        return cls(boto3.resource(cls.name, *args, **kwargs))

    def __init__(self, resource):
        self.resource = resource

    @classmethod
    def get_logger(cls):
        return logging.getLogger(cls.name)

    @classmethod
    def log_info(cls, msg, *args, **kwargs):
        cls.get_logger().info(msg, *args, **kwargs)

    @classmethod
    def log_error(cls, msg, *args, **kwargs):
        cls.get_logger().error(msg, *args, **kwargs)

    @classmethod
    def log_debug(cls, msg, *args, **kwargs):
        cls.get_logger().debug(msg, *args, **kwargs)

    @classmethod
    def log_warning(cls, msg, *args, **kwargs):
        cls.get_logger().warning(msg, *args, **kwargs)
