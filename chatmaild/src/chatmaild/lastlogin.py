import sys

from .config import read_config
from .dictproxy import DictProxy


class LastLoginDictProxy(DictProxy):
    def __init__(self, config):
        super().__init__()
        self.config = config

    def handle_set(self, transaction_id, parts):
        keyname = parts[1].split("/")
        value = parts[2] if len(parts) > 2 else ""
        addr = self.transactions[transaction_id]["addr"]
        if keyname[0] == "shared" and keyname[1] == "last-login":
            if addr.startswith("echo@"):
                return
            addr = keyname[2]
            timestamp = int(value)
            user = self.config.get_user(addr)
            user.set_last_login_timestamp(timestamp)
        else:
            # Transaction failed.
            self.transactions[transaction_id]["res"] = "F\n"


def main():
    socket, config_path = sys.argv[1:]
    config = read_config(config_path)
    dictproxy = LastLoginDictProxy(config=config)
    dictproxy.serve_forever_from_socket(socket)
