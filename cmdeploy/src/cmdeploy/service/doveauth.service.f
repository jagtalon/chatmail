[Unit]
Description=Chatmail dict authentication proxy for dovecot

[Service]
ExecStart={execpath} /run/doveauth/doveauth.socket {config_path}
Restart=always
RestartSec=30
User=vmail
RuntimeDirectory=doveauth

[Install]
WantedBy=multi-user.target
