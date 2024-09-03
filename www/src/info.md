
## More information 

{{ config.mail_domain }} provides a low-maintenance, resource efficient and 
interoperable e-mail service for everyone. What's behind a `chatmail` is 
effectively a normal e-mail address just like any other but optimized 
for the usage in chats, especially DeltaChat.

### Choosing a chatmail address instead of using a random one

In the Delta Chat account setup you may tap `Create a profile` then `Use other server` and choose `Classic e-mail login`. Here fill the two fields like this: 

- `E-Mail Address`: invent a word with
{% if username_min_length == username_max_length %}
  *exactly* {{ username_min_length }}
{% else %}
  {{ username_min_length}}
  {% if username_max_length == "more" %}
    or more
  {% else %}
    to {{ username_max_length }}
  {% endif %}
{% endif %}
  characters
  and append `@{{config.mail_domain}}` to it.

- `Existing Password`: invent at least {{ password_min_length }} characters.

If the e-mail address is not yet taken, you'll get that account. 
The first login sets your password. 


### Rate and storage limits 

- Un-encrypted messages are blocked to recipients outside
  {{config.mail_domain}} but setting up contact via [QR invite codes](https://delta.chat/en/help#howtoe2ee) 
  allows your messages to pass freely to any outside recipients.

- You may send up to {{ config.max_user_send_per_minute }} messages per minute.

- Messages are unconditionally removed {{ config.delete_mails_after }} days after arriving on the server.

- You can store up to [{{ config.max_mailbox_size }} messages on the server](https://delta.chat/en/help#what-happens-if-i-turn-on-delete-old-messages-from-server).


### <a name="account-deletion"></a> Account deletion 

If you remove a {{ config.mail_domain }} profile from within the Delta Chat app, 
then the according account on the server, along with all associated data,
is automatically deleted {{ config.delete_inactive_users_after }} days afterwards. 

If you use multiple devices 
then you need to remove the according chat profile from each device
in order for all account data to be removed on the server side. 

If you have any further questions or requests regarding account deletion
please send a message from your account to {{ config.privacy_mail }}. 


### Who are the operators? Which software is running? 

This server is a part of [Aangat Lahat](https://aangat.lahat.computer) which is run by [Jag Talon](https://jagtalon.net).
