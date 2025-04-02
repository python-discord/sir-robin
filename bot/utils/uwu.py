# This file was copied from https://github.com/python-discord/sir-lancebot
# and modified.

import random
import re
import typing as t
from dataclasses import dataclass
from functools import partial

from bot.bot import SirRobin

WORD_REPLACE = {
    "small": "smol",
    "cute": "kawaii~",
    "fluff": "floof",
    "love": "luv",
    "stupid": "baka",
    "idiot": "baka",
    "what": "nani",
    "meow": "nya~",
    "roar": "rawrr~",
}

EMOJIS = [
    "rawr x3",
    "OwO",
    "UwU",
    "o.O",
    "-.-",
    ">w<",
    "σωσ",
    "òωó",
    "ʘwʘ",
    ":3",
    "XD",
    "nyaa~~",
    "mya",
    ">_<",
    "rawr",
    "uwu",
    "^^",
    "^^;;",
]

EMOJI_REPLACE = {
    "😐": ":cat:",
    "😢": ":crying_cat_face:",
    "😍": ":heart_eyes_cat:",
    "😂": ":joy_cat:",
    "😗": ":kissing_cat:",
    "😠": ":pouting_cat:",
    "😱": ":scream_cat:",
    "😆": ":smile_cat:",
    "🙂": ":smiley_cat:",
    "😀": ":smiley_cat:",
    "😏": ":smirk_cat:",
    "🥺": ":pleading_face::point_right::point_left:"
}
REGEX_WORD_REPLACE = re.compile(r"(?<!w)[lr](?!w)")

REGEX_PUNCTUATION = re.compile(r"[.!?\r\n\t]")

REGEX_STUTTER = re.compile(r"(\s)([a-zA-Z])")
SUBSTITUTE_STUTTER = r"\g<1>\g<2>-\g<2>"

REGEX_NYA = re.compile(r"n([aeou][^aeiou])")
SUBSTITUTE_NYA = r"ny\1"

REGEX_EMOJI = re.compile(r"<(a)?:(\w+?):(\d{15,21}?)>", re.ASCII)


@dataclass(frozen=True, eq=True)
class Emoji:
    """Data class for an Emoji."""

    name: str
    uid: int
    animated: bool = False

    def __str__(self):
        anim_bit = "a" if self.animated else ""
        return f"<{anim_bit}:{self.name}:{self.uid}>"

    def can_display(self, bot: SirRobin) -> bool:
        """Determines if a bot is in a server with the emoji."""
        return bot.get_emoji(self.uid) is not None

    @classmethod
    def from_match(cls, match: tuple[str, str, str]) -> t.Optional["Emoji"]:
        """Creates an Emoji from a regex match tuple."""
        if not match or len(match) != 3 or not match[2].isdecimal():
            return None
        return cls(match[1], int(match[2]), match[0] == "a")




def _word_replace(input_string: str) -> str:
    """Replaces words that are keys in the word replacement hash to the values specified."""
    for word, replacement in WORD_REPLACE.items():
        input_string = input_string.replace(word, replacement)
    return input_string

def _char_replace(input_string: str) -> str:
    """Replace certain characters with 'w'."""
    return REGEX_WORD_REPLACE.sub("w", input_string)

def _stutter(strength: float, input_string: str) -> str:
    """Adds stuttering to a string."""
    return REGEX_STUTTER.sub(partial(_stutter_replace, strength=strength), input_string, 0)

def _stutter_replace(match: re.Match, strength: float = 0.0) -> str:
    """Replaces a single character with a stuttered character."""
    match_string = match.group()
    if random.random() < strength:
        return f"{match_string}-{match_string[-1]}"  # Stutter the last character
    return match_string

def _nyaify(input_string: str) -> str:
    """Nyaifies a string by adding a 'y' between an 'n' and a vowel."""
    return REGEX_NYA.sub(SUBSTITUTE_NYA, input_string, 0)

def _emoji(strength: float, input_string: str) -> str:
    """Replaces some punctuation with emoticons."""
    return REGEX_PUNCTUATION.sub(partial(_emoji_replace, strength=strength), input_string, 0)

def _emoji_replace(match: re.Match, strength: float = 0.0) -> str:
    """Replaces a punctuation character with an emoticon."""
    match_string = match.group()
    if random.random() < strength:
        return f" {random.choice(EMOJIS)} "
    return match_string

def _ext_emoji_replace(input_string: str) -> str:
    """Replaces any emoji the bot cannot send in input_text with a random emoticons."""
    groups = REGEX_EMOJI.findall(input_string)
    emojis = {Emoji.from_match(match) for match in groups}
    # Replace with random emoticon if unable to display
    emojis_map = {
        re.escape(str(e)): random.choice(EMOJIS)
        for e in emojis if e and not e.can_display(SirRobin)
    }
    if emojis_map:
        # Pattern for all emoji markdowns to be replaced
        emojis_re = re.compile("|".join(emojis_map.keys()))
        # Replace matches with random emoticon
        return emojis_re.sub(
            lambda m: emojis_map[re.escape(m.group())],
            input_string
        )
    # Return original if no replacement
    return input_string

def _uwu_emojis(input_string: str) -> str:
    """Replaces certain emojis with better emojis."""
    for old, new in EMOJI_REPLACE.items():
        input_string = input_string.replace(old, new)
    return input_string

def uwuify(input_string: str, *, stutter_strength: float = 0.2, emoji_strength: float = 0.1) -> str:
    """Takes a string and returns an uwuified version of it."""
    input_string = input_string.lower()
    input_string = _word_replace(input_string)
    input_string = _nyaify(input_string)
    input_string = _char_replace(input_string)
    input_string = _stutter(stutter_strength, input_string)
    input_string = _emoji(emoji_strength, input_string)
    input_string = _ext_emoji_replace(input_string)
    input_string = _uwu_emojis(input_string)
    return input_string
