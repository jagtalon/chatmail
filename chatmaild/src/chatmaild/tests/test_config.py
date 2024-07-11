import pytest
from chatmaild.config import read_config


def test_read_config_basic(example_config):
    assert example_config.mail_domain == "chat.example.org"
    assert not example_config.privacy_supervisor and not example_config.privacy_mail
    assert not example_config.privacy_pdo and not example_config.privacy_postal

    inipath = example_config._inipath
    inipath.write_text(inipath.read_text().replace("60", "37"))
    example_config = read_config(inipath)
    assert example_config.max_user_send_per_minute == 37
    assert example_config.mail_domain == "chat.example.org"


def test_read_config_testrun(make_config):
    config = make_config("something.testrun.org")
    assert config.mail_domain == "something.testrun.org"
    assert len(config.privacy_postal.split("\n")) > 1
    assert len(config.privacy_supervisor.split("\n")) > 1
    assert len(config.privacy_pdo.split("\n")) > 1
    assert config.privacy_mail == "privacy@testrun.org"
    assert config.filtermail_smtp_port == 10080
    assert config.postfix_reinject_port == 10025
    assert config.max_user_send_per_minute == 60
    assert config.max_mailbox_size == "100M"
    assert config.delete_mails_after == "20"
    assert config.username_min_length == 9
    assert config.username_max_length == 9
    assert config.password_min_length == 9
    assert "privacy@testrun.org" in config.passthrough_recipients
    assert config.passthrough_senders == []


def test_config_userstate_paths(make_config, tmp_path):
    config = make_config("something.testrun.org")
    mailboxes_dir = config.mailboxes_dir
    passdb_path = config.passdb_path
    assert mailboxes_dir.name == "something.testrun.org"
    assert passdb_path.name == "passdb.sqlite"
    assert passdb_path.is_relative_to(tmp_path)
    assert config.mail_domain == "something.testrun.org"
    path = config.get_user_maildir("user1@something.testrun.org")
    assert not path.exists()
    assert path == mailboxes_dir.joinpath("user1@something.testrun.org")

    with pytest.raises(ValueError):
        config.get_user_maildir("")

    with pytest.raises(ValueError):
        config.get_user_maildir(None)

    with pytest.raises(ValueError):
        config.get_user_maildir("../some@something.testrun.org")

    with pytest.raises(ValueError):
        config.get_user_maildir("..")

    with pytest.raises(ValueError):
        config.get_user_maildir(".")
