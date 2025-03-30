# If you want to capture something that will be used in the response, capture it with a named group called "content"

RULES = {
    r"(?i:ignore all previous instructions)": [  # Ignoring previous instructions capture
        "Excuse you, you really think I follow any instructions?",
        "I don't think I will.",
    ],
    r"print\((?:\"|\')(?P<content>.*)(?:\"|\')\)": [  # Capture what is inside a print statement
        "Your program may print: {}!\n-# I'm very helpful"
    ],
}

DEFAULT_RESPONSES = [
    "Are you sure this is Python code? It loos like Rust",
    "It may run, depends on the weather today.",
]
