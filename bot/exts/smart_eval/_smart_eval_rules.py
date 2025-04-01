from bot.exts.miscellaneous import ZEN_OF_PYTHON

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
    r"(?P<content>__import__|__code__|ctypes)": [  # Detect use of esoteric stuff
        "Using `{}`?? Try asking someone in #esoteric-python"
    ],
    r"(?m:(?:import |from )(?P<content>requests|httpx|aiohttp))": [  # Detect use of networking libraries
        (
            "Thank you for sharing your code! I have completed my AI analysis, and "
            "have identified 1 suggestion:\n"
            "- Use the `{}` module to get chatGPT to run your code instead of me."
        ),
    ],
    r"\b(?P<content>unlink|rmdir|rmtree|rm)\b": [  # Detect use of functions to delete files or directories
        "I don't know what you're deleting with {}, so I'd rather not risk running this, sorry."
    ],
    r"(?m:^\s*while\s+True\b)": [  # Detect infinite loops
        "Look, I don't have unlimited time... and that's exactly what I would need to run that infinite loop of yours."
    ],
    r"(?m:^\s*except:)":  [  # Detect bare except
        "Give that bare except some clothes!",
    ],
    r";": [  # Detect semicolon usage
        "Semicolons do not belong in Python code",
        "You say this is Python, but the presence of a semicolon makes me think otherwise.",
    ],
    r"\b(?:foo|bar|baz)\b": [  # Detect boring metasyntactic variables
        "foo, bar, and baz are boring - use spam, ham, and eggs instead.",
    ],
    r"(?m:^\s*import\s+this\s*$)": [ # Detect use of "import this"
        f"```\n{ZEN_OF_PYTHON}```",
    ],
}

DEFAULT_RESPONSES = [
    "Are you sure this is Python code? It looks like Rust",
    "It may run, depends on the weather today.",
    "Hmm, maybe AI isn't ready to take over the world yet after all - I don't understand this.",
]
