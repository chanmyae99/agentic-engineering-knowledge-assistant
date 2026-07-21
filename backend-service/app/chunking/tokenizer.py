"""
Tokenization utilities for the structure-aware chunking pipeline.

This module provides a single, reusable interface for measuring document
content. All chunking decisions should rely on this module instead of
performing ad-hoc token counting.

Current implementation
----------------------
The project currently uses a lightweight approximation based on whitespace
word boundaries. This keeps the project fast and avoids introducing model-
specific dependencies during the chunking sprint.

Future implementation
---------------------
The implementation can later be replaced with a tokenizer such as
OpenAI's ``tiktoken`` without affecting the rest of the application.
Only this module should require modification.
"""

from __future__ import annotations

import re


class Tokenizer:
    """
    Utility class for counting tokens and splitting text.

    This class centralises all token-related operations used throughout
    the chunking pipeline.

    Responsibilities
    ----------------
    - Count tokens
    - Validate token limits
    - Split text into sentences

    This class deliberately performs no chunking logic.
    """

    # Regular expression used to detect sentence boundaries.
    _SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")

    @staticmethod
    def count_tokens(text: str) -> int:
        """
        Estimate the number of tokens contained in the given text.

        The current implementation approximates tokens using whitespace-
        separated words.

        Parameters
        ----------
        text:
            Input text.

        Returns
        -------
        int
            Estimated token count.
        """
        if not text.strip():
            return 0

        return len(text.split())

    @staticmethod
    def split_sentences(text: str) -> list[str]:
        """
        Split text into individual sentences.

        Parameters
        ----------
        text:
            Input text.

        Returns
        -------
        list[str]
            Ordered list of cleaned sentences.
        """
        if not text.strip():
            return []

        sentences = Tokenizer._SENTENCE_PATTERN.split(text)

        return [
            sentence.strip()
            for sentence in sentences
            if sentence.strip()
        ]

    @staticmethod
    def is_within_limit(
        text: str,
        max_tokens: int,
    ) -> bool:
        """
        Check whether the text is within the specified token limit.

        Parameters
        ----------
        text:
            Input text.

        max_tokens:
            Maximum allowed token count.

        Returns
        -------
        bool
            True if the text is within the limit.
        """
        return Tokenizer.count_tokens(text) <= max_tokens