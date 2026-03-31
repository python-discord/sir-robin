# Rules format
Each rule should be in the following format:
```toml
[[rule]]
type = "message" | "reaction"
reaction_content = []  # each list item should be the name of a reaction or the reaction unicode itself
message_content = '''...'''  # this should be a valid regex that can be compiled
points = 0  # the number of points that should be added
```

You can have multiple triggers with different point values for each rule file. 
Each rule trigger is independent of each other. Any of them can trigger, they do not all have to trigger for points to be given.

Notes:
- Each rule trigger needs to start with `[[rule]]`
- `reaction_content` - If the reaction is a default reaction, it should be the unicode emoji itself. If the reaction is a custom one, use the reaction name.
- `message_content` - Use triple quotes to avoid an escaping problem within toml, especially with regex.
- `points` - Can be a negative number.

Examples of different rules:
```toml
[[rule]]
type = "message"
message_content = '''\b((?:p|P)ython)\b'''
points = 1
```

```toml
[[rule]]
type = "reaction"
reaction_content = ["🦀", "rust"]
points = -1
```

```toml
[[rule]]
interaction_type = "message"
message_content = '''((?:b|B)lazing(?:ly)*\sfast)'''
points = -1

[[rule]]
interaction_type = "message"
message_content = '''(?:🚀)+.*((?:b|B)lazing(?:ly)*\sfast).*(?:🚀)+'''
points = -2
# A message that with the rocket emojis *and* blazing(ly) fast will get a total of -3 points with these triggers
```