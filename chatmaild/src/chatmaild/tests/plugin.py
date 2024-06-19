import importlib.resources
import itertools
import os
import random
from email import policy
from email.parser import BytesParser
from pathlib import Path

import pytest
from chatmaild.config import read_config, write_initial_config
from chatmaild.database import Database


@pytest.fixture
def make_config(tmp_path):
    inipath = tmp_path.joinpath("chatmail.ini")

    def make_conf(mail_domain):
        write_initial_config(inipath, mail_domain=mail_domain)
        return read_config(inipath)

    return make_conf


@pytest.fixture
def example_config(make_config):
    return make_config("chat.example.org")


@pytest.fixture
def maildomain(example_config):
    return example_config.mail_domain


@pytest.fixture
def gencreds(maildomain):
    count = itertools.count()
    next(count)

    def gen(domain=None):
        domain = domain if domain else maildomain
        while 1:
            num = next(count)
            alphanumeric = "abcdefghijklmnopqrstuvwxyz1234567890"
            user = "".join(random.choices(alphanumeric, k=10))
            user = f"ac{num}_{user}"[:9]
            password = "".join(random.choices(alphanumeric, k=12))
            yield f"{user}@{domain}", f"{password}"

    return lambda domain=None: next(gen(domain))


@pytest.fixture()
def db(tmpdir):
    db_path = tmpdir / "passdb.sqlite"
    print("database path:", db_path)
    return Database(db_path)


@pytest.fixture
def maildata(request):
    try:
        datadir = importlib.resources.files(__package__).joinpath("mail-data")
    except TypeError:
        # in python3.9 or lower, the above doesn't work, so we get datadir this way:
        datadir = Path(os.getcwd()).joinpath("chatmaild/src/chatmaild/tests/mail-data")

    assert datadir.exists(), datadir

    def maildata(name, from_addr, to_addr):
        # Using `.read_bytes().decode()` instead of `.read_text()` to preserve newlines.
        data = datadir.joinpath(name).read_bytes().decode()

        text = data.format(from_addr=from_addr, to_addr=to_addr)
        return BytesParser(policy=policy.default).parsebytes(text.encode())

    return maildata
