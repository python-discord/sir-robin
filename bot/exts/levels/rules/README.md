# Rules format
Each rule should be in the following format:
```toml
type = "message" | "reaction"
reaction_content = []  # each list item should be the name of a reaction or the reaction unicode itself
message_content = '''...'''  # this should be a valid regex that can be compiled
points = 0  # the number of points that should be added
```

Notes:
- `reaction_content` - If the reaction is a default reaction, it should be the unicode emoji itself. If the reaction is a custom one, use the reaction name.
- `message_content` - Use triple quotes to avoid an escaping problem within toml, especially with regex.
- `points` - Can be a negative number.

Examples of different rules:
```toml
type = "message"
message_content = '''\b((?:p|P)ython)\b'''
points = 1
```

```toml
type = "reaction"
reaction_content = ["🦀", "rust"]
points = -1
```