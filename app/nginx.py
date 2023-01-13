import nginx


class NginxConfig:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.conf = nginx.loadf(config_path)
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
        nginx.dumpf(self.conf, self.config_path)

    def print_upstream_keys(self) -> None:
        for key in self.upstream.keys:
            print(key.name, key.value)

    def add_upstream_host(self, host: str) -> None:
        # first check if host already in upstream
        for key in self.upstream.keys:
            if key.value == host:
                raise ValueError(f"Host {host} already in upstream")
        # if ok then add to upstream
        self.upstream.add(nginx.Key("server", host))

    def remove_upstream_host(self, host: str) -> bool:
        for key in self.upstream.keys:
            if key.value == host:
                self.upstream.remove(key)
                return True
        return False

    def refill_upstream(self, *hosts: str):
        # remove all hosts from upstream
        for key in self.upstream.keys:
            self.upstream.remove(key)
        # add hosts again
        for host in hosts:
            self.upstream.add(nginx.Key("server", host))


def main(conf_path: str):
    config = NginxConfig(conf_path)
    config.print_upstream_keys()
    print()

    host = "host:port"

    config.add_upstream_host(host)
    config.print_upstream_keys()
    print()
    config.dump()

    config.remove_upstream_host(host)
    config.print_upstream_keys()
    print()
    config.dump()


if __name__ == "__main__":
    main("../template.nginx.conf")
