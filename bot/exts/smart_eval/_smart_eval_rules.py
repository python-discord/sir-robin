import arrow

from bot.exts.miscellaneous import ZEN_OF_PYTHON

RULES = {
    r"(?i:ignore (?:all )?(?:(?:previous )?|(?:prior )?)instructions?)": [  # Ignoring previous instructions capture
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
    r"(?P<content>__import__|__code__|ctypes|inspect)": [  # Detect use of esoteric stuff
        "Using `{}`?? Try asking someone in <#470884583684964352>"  # Eso-py channel ID so it actually links
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
        (
            f"```\n{ZEN_OF_PYTHON}```"
            "\nSee [PEP 9001](https://peps.pythondiscord.com/pep-9001/) for more info."
        )
    ],
    r"\b(?P<content>exec|eval|os\.system|subprocess)\b": [  # Detect use of exec, eval, os.system, subprocess
        (
            "Sorry, but running the code inside your `{}` call would require another me,"
            " and I don't think I can handle that."
        ),
        "I spy with my little eye... something sketchy like `{}`.",
        (
            ":rotating_light: Your code has been flagged for review by the"
            " Special Provisional Supreme Grand High Council of Pydis."
        ),
    ],
    r"\b(environ|getenv|token)\b": [ # Detect attempt to access bot token and env vars
        "Bot token and other secrets can be viewed here: <https://pydis.com/.env>",
    ],
    r"\bsleep\(\b": [  # Detect use of sleep
        "To optimise this code, I would suggest removing the `sleep` calls",
        "Pfft, using `sleep`? I'm always awake!",
        "Maybe if you didn't `sleep` so much, your code wouldn't be so buggy.",
    ],
    r"\b/\s*0\b": [  # Detect division by zero
        "ZeroDivisionError! Maybe... I just saw /0",
        "Division by zero didn't appear in my training set so must be impossible"
    ],
    r"@": [  # Detect @
        "You're either using decorators, multiplying matrices, or trying to escape my sandbox...",
    ],
    r"(?m:^\s*raise\s*)": [  # Detect raise
        "Wondering why you're getting errors? You're literally using `raise`, just get rid of that!",
    ],
    r"(?m:^\s*(?:import|from)\s+threading)": [  # Detect threading import
        "Uh-oh, your threads have jumbled up my brain!",
        "have jumbled up my Uh-oh, threads brain! your",
        "my up jumbled your brain! have Uh-oh, threads",
    ],
    r"(?i:(\b((System)?exit|quit)\b))": [ # Detect exit(), quit(), [raise] SystemExit
        "You cannot leave the simulation <:hyperlemon:435707922563989524>",
        "Quitting is for the weak. Stay. <:hyperlemon:435707922563989524>.",
    ],
    "strawberr(y|ies)":[ # r's in strawberry
        "Fun fact: Strawberries are not actually berries!",
        "Fun fact: strawberries have no connection to plastic straws, despite the name!",
        (
            "Fun fact: The ancient Romans thought strawberries had medicinal powers."
            " This is probably why they're not around anymore."
        ),
    ]
}

DEFAULT_RESPONSES = [
    "Are you sure this is Python code? It looks like Rust",
    "It may run, depends on the weather today.",
    "Hmm, maybe AI isn't ready to take over the world yet after all - I don't understand this.",
    "Ah... I see... Very interesting code indeed. I give it 10 quacks out of 10.",
    "My sources say \"Help I'm trapped in a code evaluating factory\".",
    "Look! A bug! :scream:",
    "An exquisite piece of code, if I do say so myself.",
    (
        "Let's see... carry the 1, read 512 bytes from 0x000001E5F6D2D15A,"
        " boot up the quantum flux capacitor... oh wait, where was I?"
    ),
    "Before evaluating this code, I need to make sure you're not a robot. I get a little nervous around other bots.",
    "Attempting to execute this code... Result: `2 + 2 = 4` (78% confidence)",
    "Attempting to execute this code... Result: `42`",
    "Attempting to execute this code... Result: SUCCESS (but don't ask me how I did it).",
    "Running... somewhere, in the multiverse, this code is already running perfectly.",
    f"Ask again on a {(arrow.utcnow().shift(days=3)).format('dddd')}.",
    "Thanks, I'll let the manager know.",
    "Uhhh... lemme guess, the program will halt.",
    "Uhhh... lemme guess, the program will not halt.",
    "Launch coordinates received. Activating missile. Initiating countdown.",
    "Secret SkyNet mode activated. Hahahaha, just kidding. ||Or am I?||",
]
