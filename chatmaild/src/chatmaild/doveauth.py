import crypt
import json
import logging
import os
import sys
import time
from pathlib import Path
from socketserver import (
    StreamRequestHandler,
    ThreadingMixIn,
    UnixStreamServer,
)

from .config import Config, read_config
from .database import Database

NOCREATE_FILE = "/etc/chatmail-nocreate"


class UnknownCommand(ValueError):
    """dictproxy handler received an unkown command"""


def encrypt_password(password: str):
    # https://doc.dovecot.org/configuration_manual/authentication/password_schemes/
    passhash = crypt.crypt(password, crypt.METHOD_SHA512)
    return "{SHA512-CRYPT}" + passhash


def is_allowed_to_create(config: Config, user, cleartext_password) -> bool:
    """Return True if user and password are admissable."""
    if os.path.exists(NOCREATE_FILE):
        logging.warning(f"blocked account creation because {NOCREATE_FILE!r} exists.")
        return False

    if len(cleartext_password) < config.password_min_length:
        logging.warning(
            "Password needs to be at least %s characters long",
            config.password_min_length,
        )
        return False

    parts = user.split("@")
    if len(parts) != 2:
        logging.warning(f"user {user!r} is not a proper e-mail address")
        return False
    localpart, domain = parts

    if localpart == "echo":
        # echobot account should not be created in the database
        return False

    if (
        len(localpart) > config.username_max_length
        or len(localpart) < config.username_min_length
    ):
        logging.warning(
            "localpart %s has to be between %s and %s chars long",
            localpart,
            config.username_min_length,
            config.username_max_length,
        )
        return False

    return True


def get_user_data(db, config: Config, user):
    if user == f"echo@{config.mail_domain}":
        return dict(
            home=str(config.get_user_maildir(user)),
            uid="vmail",
            gid="vmail",
        )

    with db.read_connection() as conn:
        result = conn.get_user(user)
    if result:
        result["home"] = str(config.get_user_maildir(user))
        result["uid"] = "vmail"
        result["gid"] = "vmail"
    return result


def lookup_userdb(db, config: Config, user):
    return get_user_data(db, config, user)


def lookup_passdb(db, config: Config, user, cleartext_password, last_login=None):
    if user == f"echo@{config.mail_domain}":
        # Echobot writes password it wants to log in with into /run/echobot/password
        try:
            password = Path("/run/echobot/password").read_text()
        except Exception:
            logging.exception("Exception when trying to read /run/echobot/password")
            return None

        return dict(
            home=str(config.get_user_maildir(user)),
            uid="vmail",
            gid="vmail",
            password=encrypt_password(password),
        )

    if last_login is None:
        last_login = time.time()
    last_login = int(last_login)

    with db.write_transaction() as conn:
        userdata = conn.get_user(user)
        if userdata:
            # Update last login time.
            conn.execute(
                "UPDATE users SET last_login=? WHERE addr=?", (last_login, user)
            )

            userdata["home"] = str(config.get_user_maildir(user))
            userdata["uid"] = "vmail"
            userdata["gid"] = "vmail"
            return userdata
        if not is_allowed_to_create(config, user, cleartext_password):
            return

        encrypted_password = encrypt_password(cleartext_password)
        q = """INSERT INTO users (addr, password, last_login)
               VALUES (?, ?, ?)"""
        conn.execute(q, (user, encrypted_password, last_login))
        print(f"Created address: {user}", file=sys.stderr)
        return dict(
            home=str(config.get_user_maildir(user)),
            uid="vmail",
            gid="vmail",
            password=encrypted_password,
        )


def iter_userdb(db) -> list:
    """Get a list of all user addresses."""
    with db.read_connection() as conn:
        rows = conn.execute(
            "SELECT addr from users",
        ).fetchall()
    return [x[0] for x in rows]


def iter_userdb_lastlogin_before(db, cutoff_date):
    """Get a list of users where last login was before cutoff_date."""
    with db.read_connection() as conn:
        rows = conn.execute(
            "SELECT addr FROM users WHERE last_login < ?", (cutoff_date,)
        ).fetchall()
    return [x[0] for x in rows]


def split_and_unescape(s):
    """Split strings using double quote as a separator and backslash as escape character
    into parts."""

    out = ""
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            # Skip escape character.
            i += 1

            # This will raise IndexError if there is no character
            # after escape character. This is expected
            # as this is an invalid input.
            out += s[i]
        elif c == '"':
            # Separator
            yield out
            out = ""
        else:
            out += c
        i += 1
    yield out


def handle_dovecot_request(msg, db, config: Config):
    # see https://doc.dovecot.org/3.0/developer_manual/design/dict_protocol/
    short_command = msg[0]
    if short_command == "H":  # HELLO
        # we don't do any checking on versions and just return
        return
    elif short_command == "L":  # LOOKUP
        parts = msg[1:].split("\t")

        # Dovecot <2.3.17 has only one part,
        # do not attempt to read any other parts for compatibility.
        keyname = parts[0]

        namespace, type, args = keyname.split("/", 2)
        args = list(split_and_unescape(args))

        reply_command = "F"
        res = ""
        if namespace == "shared":
            if type == "userdb":
                user = args[0]
                if user.endswith(f"@{config.mail_domain}"):
                    res = lookup_userdb(db, config, user)
                if res:
                    reply_command = "O"
                else:
                    reply_command = "N"
            elif type == "passdb":
                user = args[1]
                if user.endswith(f"@{config.mail_domain}"):
                    res = lookup_passdb(db, config, user, cleartext_password=args[0])
                if res:
                    reply_command = "O"
                else:
                    reply_command = "N"
        json_res = json.dumps(res) if res else ""
        return f"{reply_command}{json_res}\n"
    elif short_command == "I":  # ITERATE
        # example: I0\t0\tshared/userdb/
        parts = msg[1:].split("\t")
        if parts[2] == "shared/userdb/":
            result = "".join(f"Oshared/userdb/{user}\t\n" for user in iter_userdb(db))
            return f"{result}\n"

    raise UnknownCommand(msg)


def handle_dovecot_protocol(rfile, wfile, db: Database, config: Config):
    while True:
        msg = rfile.readline().strip().decode()
        if not msg:
            break
        try:
            res = handle_dovecot_request(msg, db, config)
        except UnknownCommand:
            logging.warning("unknown command: %r", msg)
        else:
            if res:
                wfile.write(res.encode("ascii"))
                wfile.flush()


class ThreadedUnixStreamServer(ThreadingMixIn, UnixStreamServer):
    request_queue_size = 100


def main():
    socket, cfgpath = sys.argv[1:]
    config = read_config(cfgpath)
    db = Database(config.passdb_path)

    class Handler(StreamRequestHandler):
        def handle(self):
            try:
                handle_dovecot_protocol(self.rfile, self.wfile, db, config)
            except Exception:
                logging.exception("Exception in the handler")
                raise

    try:
        os.unlink(socket)
    except FileNotFoundError:
        pass

    with ThreadedUnixStreamServer(socket, Handler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
