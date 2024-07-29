#!/usr/bin/env python3
"""Advanced echo bot example.

it will echo back any message that has non-empty text and also supports the /help command.
"""

import logging
import os
import subprocess
import sys

from deltachat_rpc_client import Bot, DeltaChat, EventType, Rpc, events

from chatmaild.config import echobot_password_path, read_config
from chatmaild.doveauth import encrypt_password
from chatmaild.newemail import create_newemail_dict

hooks = events.HookCollection()


@hooks.on(events.RawEvent)
def log_event(event):
    if event.kind == EventType.INFO:
        logging.info(event.msg)
    elif event.kind == EventType.WARNING:
        logging.warning(event.msg)


@hooks.on(events.RawEvent(EventType.ERROR))
def log_error(event):
    logging.error("%s", event.msg)


@hooks.on(events.MemberListChanged)
def on_memberlist_changed(event):
    logging.info(
        "member %s was %s", event.member, "added" if event.member_added else "removed"
    )


@hooks.on(events.GroupImageChanged)
def on_group_image_changed(event):
    logging.info("group image %s", "deleted" if event.image_deleted else "changed")


@hooks.on(events.GroupNameChanged)
def on_group_name_changed(event):
    logging.info(f"group name changed, old name: {event.old_name}")


@hooks.on(events.NewMessage(func=lambda e: not e.command))
def echo(event):
    snapshot = event.message_snapshot
    if snapshot.is_info:
        # Ignore info messages
        return
    if snapshot.text or snapshot.file:
        snapshot.chat.send_message(text=snapshot.text, file=snapshot.file)


@hooks.on(events.NewMessage(command="/help"))
def help_command(event):
    snapshot = event.message_snapshot
    snapshot.chat.send_text("Send me any message and I will echo it back")


def main():
    logging.basicConfig(level=logging.INFO)
    path = os.environ.get("PATH")
    venv_path = sys.argv[0].strip("echobot")
    os.environ["PATH"] = path + ":" + venv_path
    with Rpc() as rpc:
        deltachat = DeltaChat(rpc)
        system_info = deltachat.get_system_info()
        logging.info(f"Running deltachat core {system_info.deltachat_core_version}")

        accounts = deltachat.get_all_accounts()
        account = accounts[0] if accounts else deltachat.add_account()

        bot = Bot(account, hooks)

        config = read_config(sys.argv[1])
        addr = "echo@" + config.mail_domain

        # Create password file
        if bot.is_configured():
            password = bot.account.get_config("mail_pw")
        else:
            password = create_newemail_dict(config)["password"]

        echobot_password_path.write_text(encrypt_password(password))
        # Give the user which doveauth runs as access to the password file.
        subprocess.check_call(
            ["/usr/bin/setfacl", "-m", "user:vmail:r", echobot_password_path],
        )

        if not bot.is_configured():
            bot.configure(addr, password)

        bot.run_forever()


if __name__ == "__main__":
    main()
