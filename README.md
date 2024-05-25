
<img width="800px" src="www/src/collage-top.png"/>

# Chatmail services optimized for Delta Chat apps 

This repository helps to setup a ready-to-use chatmail server
comprised of a minimal setup of the battle-tested 
[postfix smtp](https://www.postfix.org) and [dovecot imap](https://www.dovecot.org) services. 

The setup is designed and optimized for providing chatmail accounts 
for use by [Delta Chat apps](https://delta.chat).

Chatmail accounts are automatically created by a first login, 
after which the initially specified password is required for using them. 

## Deploying your own chatmail server 

To deploy chatmail on your own server, you must have set-up ssh authentication and need to use an ed25519 key, due to an [upstream bug in paramiko](https://github.com/paramiko/paramiko/issues/2191). You also need to add your private key to the local ssh-agent, because you can't type in your password during deployment.

We use `chat.example.org` as the chatmail domain in the following steps. 
Please substitute it with your own domain. 

1. Install the `cmdeploy` command in a virtualenv

   ```
    git clone https://github.com/deltachat/chatmail
    cd chatmail
    scripts/initenv.sh
   ```

2. Create chatmail configuration file `chatmail.ini`:

   ```
    scripts/cmdeploy init chat.example.org  # <-- use your domain 
   ```

3. Setup first DNS records for your chatmail domain, 
   according to the hints provided by `cmdeploy init`.
   Verify that SSH root login works:

   ```
    ssh root@chat.example.org   # <-- use your domain 
   ```

4. Deploy to the remote chatmail server:

   ```
    scripts/cmdeploy run
   ```
   This script will also show you additional DNS records
   which you should configure at your DNS provider
   (it can take some time until they are public).

### Other helpful commands:

To check the status of your remotely running chatmail service:

```
scripts/cmdeploy status
```

To check whether your DNS records are correct:

```
scripts/cmdeploy dns
```

To test whether your chatmail service is working correctly:

```
scripts/cmdeploy test
```

To measure the performance of your chatmail service:

```
scripts/cmdeploy bench
```

## Overview of this repository

This repository drives the development of chatmail services, 
comprised of minimal setups of

- [postfix smtp server](https://www.postfix.org)
- [dovecot imap server](https://www.dovecot.org)

as well as custom services that are integrated with these two:

- `chatmaild/src/chatmaild/doveauth.py` implements
  create-on-login account creation semantics and is used
  by Dovecot during login authentication and by Postfix
  which in turn uses [Dovecot SASL](https://doc.dovecot.org/configuration_manual/authentication/dict/#complete-example-for-authenticating-via-a-unix-socket)
  to authenticate users
  to send mails for them.

- `chatmaild/src/chatmaild/filtermail.py` prevents
  unencrypted e-mail from leaving the chatmail service
  and is integrated into postfix's outbound mail pipelines.

There is also the `cmdeploy/src/cmdeploy/cmdeploy.py` command line tool
which helps with setting up and managing the chatmail service.
`cmdeploy run` uses [pyinfra-based scripting](https://pyinfra.com/)
in `cmdeploy/src/cmdeploy/__init__.py`
to automatically install all chatmail components on a server.


### Home page and getting started for users

`cmdeploy run` also creates default static Web pages and deploys them
to a nginx web server with: 

- a default `index.html` along with a QR code that users can click to
  create accounts on your chatmail provider,

- a default `info.html` that is linked from the home page,

- a default `policy.html` that is linked from the home page.

All `.html` files are generated
by the according markdown `.md` file in the `www/src` directory.


### Refining the web pages


```
scripts/cmdeploy webdev
```

This starts a local live development cycle for chatmail Web pages:

- uses the `www/src/page-layout.html` file for producing static
  HTML pages from `www/src/*.md` files

- continously builds the web presence reading files from `www/src` directory
  and generating html files and copying assets to the `www/build` directory.

- Starts a browser window automatically where you can "refresh" as needed.


## Emergency Commands to disable automatic account creation

If you need to stop account creation,
e.g. because some script is wildly creating accounts,
login to the server with ssh and run:

```
    touch /etc/chatmail-nocreate
```

While this file is present, account creation will be blocked.

### Ports

[Postfix](http://www.postfix.org/) listens on ports 25 (smtp) and 587 (submission) and 465 (submissions).
[Dovecot](https://www.dovecot.org/) listens on ports 143 (imap) and 993 (imaps).
[nginx](https://www.nginx.com/) listens on port 443 (https).
[acmetool](https://hlandau.github.io/acmetool/) listens on port 80 (http).

Delta Chat apps will, however, discover all ports and configurations
automatically by reading the [autoconfig XML file](https://www.ietf.org/archive/id/draft-bucksch-autoconfig-00.html) from the chatmail service.

## Email authentication

chatmail servers rely on [DKIM](https://www.rfc-editor.org/rfc/rfc6376)
to authenticate incoming emails.
Incoming emails must have a valid DKIM signature with
Signing Domain Identifier (SDID, `d=` parameter in the DKIM-Signature header)
equal to the `From:` header domain.
This property is checked by OpenDKIM screen policy script
before validating the signatures.
This correpsonds to strict [DMARC](https://www.rfc-editor.org/rfc/rfc7489) alignment (`adkim=s`),
but chatmail does not rely on DMARC and does not consult the sender policy published in DMARC records.
Other legacy authentication mechanisms such as [iprev](https://www.rfc-editor.org/rfc/rfc8601#section-2.7.3)
and [SPF](https://www.rfc-editor.org/rfc/rfc7208) are also not taken into account.
If there is no valid DKIM signature on the incoming email,
the sender receives a "5.7.1 No valid DKIM signature found" error.

Outgoing emails must be sent over authenticated connection
with envelope MAIL FROM (return path) corresponding to the login.
This is ensured by Postfix which maps login username
to MAIL FROM with
[`smtpd_sender_login_maps`](https://www.postfix.org/postconf.5.html#smtpd_sender_login_maps)
and rejects incorrectly authenticated emails with [`reject_sender_login_mismatch`](reject_sender_login_mismatch) policy.
`From:` header must correspond to envelope MAIL FROM,
this is ensured by `filtermail` proxy.
