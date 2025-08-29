---
hide: footer
---
# `ex.User`

A user in Extralit is a profile that uses the SDK or UI. Their profile can be used to track their feedback activity and to manage their access to the Extralit server.

## Usage Examples

To create a new user, instantiate the `User` object with the client and the username:

```python
user = ex.User(username="my_username", password="my_password")
user.create()
```

Existing users can be retrieved by their username:

```python
user = client.users("my_username")
```

The current user of the `ex.Extralit` client can be accessed using the `me` attribute:

```python
client.me
```

---

::: src.extralit.users._resource.User
