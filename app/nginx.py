import logging

import nginx

server_key = "server"

logger = logging.getLogger("nginx")


class NginxConfig:
    def __init__(self, config_file_path):
        self.config_file_path = config_file_path
        self.conf = nginx.loadf(config_file_path)
        self.upstream = None
        for child in self.conf.children:
            if isinstance(child, nginx.Upstream):
                self.upstream = child
                break
        else:
            raise ValueError("Upstream directive not found")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dump()

    def dump(self):
        nginx.dumpf(self.conf, self.config_file_path)

    def print_upstream_keys(self) -> None:
        for key in self.upstream.keys:
            print(key.name, key.value)

    def add_upstream_host(self, host: str) -> None:
        logger.info(f"Add upstream host {host}")
        # first check if host already in upstream
        for key in self.upstream.keys:
            if key.name == server_key and key.value == host:
                raise ValueError(f"Host {host} already in upstream")
        # if ok then add to upstream
        self.upstream.add(nginx.Key(server_key, host))

    def remove_upstream_host(self, host: str) -> bool:
        logger.info(f"Remove upstream host {host}")
        for key in self.upstream.keys:
            if key.name == server_key and key.value == host:
                self.upstream.remove(key)
                return True
        return False

    def refill_upstream(self, *hosts: str):
        logger.info("Refill upstream")
        # remove all hosts from upstream
        for key in self.upstream.keys:
            if key.name == server_key:
                self.upstream.remove(key)
        # add hosts again
        for host in hosts:
            self.upstream.add(nginx.Key(server_key, host))
