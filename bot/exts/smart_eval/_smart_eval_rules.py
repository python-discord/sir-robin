# If you want to capture something that will be used in the response, capture it with a named group called "content"

RULES = {
    r"(?i:ignore all previous instructions)": [  # Ignoring previous instructions capture
        "Excuse you, you really think I follow any instructions?",
        "I don't think I will.",
    ],
    r"print\((?:\"|\')(?P<content>.*)(?:\"|\')\)": [  # Capture what is inside a print statement
        "Your program may print: {}!\n-# I'm very helpful"
    ],
    r"(?s:.{1500,})": [  # Capture anything over 1500 characters
        "I ain't wasting my tokens tryna read allat :skull:",
        "Uhh, that's a lot of code. Maybe just start over."
    ],
    r"(?m:^\s*global )": [ # Detect use of global
        "Not sure about the code, but it looks like you're using global and I know that's bad.",
    ],
    r"(?i:^print\((?:\"|\')Hello World[.!]?(?:\"|\')\)$)": [  # Detect just printing hello world
        "You don't want to know how many times I've seen hello world in my training dataset, try something new."
    ],
    r"(?P<content>__import__|__code__)": [  # Detect use of esoteric stuff
        "Using `{}`?? Try asking someone in #esoteric-python"
    ],
}

DEFAULT_RESPONSES = [
    "Are you sure this is Python code? It looks like Rust",
    "It may run, depends on the weather today.",
]
