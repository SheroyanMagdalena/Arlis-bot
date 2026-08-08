"""Rules for detecting legal topics whose answer depends on a reference date even
when the question itself uses no temporal wording (e.g. "how much is child benefit?").
"""

from __future__ import annotations

import re

# Curated Armenian legal topics known to be tiered/conditioned by date (child's age,
# benefit-eligibility windows, law-version effective dates, etc.).
DATE_DEPENDENT_TOPICS = [
    "մանկական նպաստ",  # child benefit
    "ծննդյան նպաստ",  # birth benefit
    "կենսաթոշակ",  # pension
    "ալիմենտ",  # alimony
    "նվազագույն աշխատավարձ",  # minimum wage
    "գործազրկության նպաստ",  # unemployment benefit
    "ընտանեկան նպաստ",  # family benefit
]

# Only a leading word boundary is enforced, not a trailing one: Armenian is heavily
# inflected and attaches case suffixes directly to the noun with no space (e.g. the
# genitive "նպաստի" for "նպաստ"), so requiring a trailing boundary would miss most
# real questions that use the topic noun in anything but its bare dictionary form.
#
# Multi-word topics are matched as a bag of per-word patterns rather than one
# contiguous phrase: real questions insert modifiers between the topic's words (e.g.
# "նվազագույն ամսական աշխատավարձ" — "minimum MONTHLY wage" — inserts "ամսական"
# into "նվազագույն աշխատավարձ"), which a literal phrase match would miss entirely.
_TOPIC_PATTERNS = [
    (topic, [re.compile(r"(?<!\w)" + re.escape(word)) for word in topic.split()])
    for topic in DATE_DEPENDENT_TOPICS
]

# Second-chance detector: retrieved article text that itself carries date/age/amount
# threshold language, for topics not on the curated list above.
DATE_PATTERN_MARKERS = [
    re.compile(r"-ից\s+մինչև"),  # "from ... until ..."
    re.compile(r"տարեկան\s+հասակ"),  # "... years of age"
    re.compile(r"թվականից"),  # "as of [year]"
    re.compile(r"\bմինչև\s+\d"),  # "until/up to <number>"
]


def matches_date_dependent_topic(question: str) -> list[str]:
    normalized = question.lower()
    return [
        topic
        for topic, word_patterns in _TOPIC_PATTERNS
        if all(pattern.search(normalized) for pattern in word_patterns)
    ]


def has_date_conditional_language(text: str) -> bool:
    return any(pattern.search(text) for pattern in DATE_PATTERN_MARKERS)
