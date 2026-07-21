"""
Text-cleaning utilities for the structure-aware chunking pipeline.

The cleaner normalises text extracted from PDF and DOCX documents before
structure detection and chunk construction.

Its responsibilities include:

- normalising line endings and whitespace
- repairing words broken by line-ending hyphens
- normalising bullet symbols
- removing standalone page-number lines
- conservatively joining wrapped lines
- removing repeated PDF headers and footers

The cleaner deliberately does not:

- detect document headings or sections
- calculate chunk boundaries
- count tokens
- generate embeddings
- access Azure Blob Storage
"""

from __future__ import annotations

import re
from collections import Counter


class TextCleaner:
    """
    Clean text while preserving useful document structure.

    The implementation is intentionally conservative. Engineering documents
    often contain headings, numbered clauses, bullet lists, and tables.
    Excessive cleaning could remove or combine information that the later
    structure analyser needs.

    Therefore, this class focuses on normalisation and obvious extraction
    artefacts rather than attempting to understand document meaning.
    """

    # Matches spaces and tabs while preserving newline characters.
    _HORIZONTAL_WHITESPACE_PATTERN = re.compile(r"[^\S\r\n]+")

    # Matches three or more consecutive blank lines.
    _EXCESSIVE_NEWLINES_PATTERN = re.compile(r"\n{3,}")

    # Matches a word split across a line boundary, for example:
    # "manu-\nfacturing" -> "manufacturing"
    #
    # The next part must begin with a lowercase letter. This reduces the risk
    # of incorrectly combining a heading or separate capitalised term.
    _HYPHENATED_LINE_BREAK_PATTERN = re.compile(
        r"(?<=\w)-[ \t]*\n[ \t]*(?=[a-z])"
    )

    # Matches lines containing only a page number or common page-number text.
    _PAGE_NUMBER_PATTERN = re.compile(
        r"^(?:page\s+)?\d+(?:\s+of\s+\d+)?$",
        flags=re.IGNORECASE,
    )

    # Common bullet characters produced by PDF and DOCX extraction.
    _BULLET_PATTERN = re.compile(r"^[\u2022\u2023\u25E6\u2043\u2219]\s*")

    # A line beginning with one of these patterns should remain separate.
    _LIST_ITEM_PATTERN = re.compile(
        r"^(?:"
        r"[-*]\s+|"                 # Hyphen or asterisk bullet
        r"\d+[.)]\s+|"              # 1. or 1)
        r"[a-zA-Z][.)]\s+|"          # a. or A)
        r"\([a-zA-Z0-9]+\)\s+"       # (a), (1), etc.
        r")"
    )

    # A numbered heading such as:
    # 1 Introduction
    # 2.3 Risk Assessment
    # 4.2.1 General Requirements
    _NUMBERED_HEADING_PATTERN = re.compile(
        r"^\d+(?:\.\d+){0,5}\.?\s+\S+"
    )

    _TERMINAL_PUNCTUATION = (".", "!", "?", ":", ";")

    @classmethod
    def clean_text(cls, text: str) -> str:
        """
        Clean one block of extracted document text.

        Processing is performed in a stable order so that each operation works
        on predictable input.

        Parameters
        ----------
        text:
            Raw text extracted from a PDF page, DOCX paragraph, table, or other
            document element.

        Returns
        -------
        str
            Cleaned text with important line and paragraph structure retained.
            An empty or whitespace-only input returns an empty string.
        """
        if not text or not text.strip():
            return ""

        cleaned = cls._normalise_line_endings(text)
        cleaned = cls._repair_hyphenated_line_breaks(cleaned)
        cleaned = cls._normalise_horizontal_whitespace(cleaned)

        lines = cleaned.split("\n")
        lines = cls._clean_individual_lines(lines)
        lines = cls._merge_wrapped_lines(lines)

        cleaned = "\n".join(lines)
        cleaned = cls._remove_excessive_blank_lines(cleaned)

        return cleaned.strip()

    @classmethod
    def clean_pages(
        cls,
        pages: list[str],
        repetition_ratio: float = 0.6,
        minimum_pages: int = 3,
    ) -> list[str]:
        """
        Clean multiple PDF pages and remove repeated headers and footers.

        A header or footer candidate is considered repeated when the same
        normalised line appears on at least ``repetition_ratio`` of eligible
        pages.

        Only the first and last non-empty line of each page are considered.
        This conservative approach reduces the chance of deleting legitimate
        body content.

        Parameters
        ----------
        pages:
            PDF page texts in their original order.

        repetition_ratio:
            Fraction of pages on which a candidate must appear before it is
            treated as a repeated header or footer. The value must be between
            0 and 1.

        minimum_pages:
            Minimum number of pages required before repeated margin detection
            is attempted.

        Returns
        -------
        list[str]
            Cleaned page texts in the same order as the input.

        Raises
        ------
        ValueError
            If ``repetition_ratio`` is outside the range 0 to 1 or if
            ``minimum_pages`` is less than 1.
        """
        if not 0 < repetition_ratio <= 1:
            raise ValueError(
                "repetition_ratio must be greater than 0 and at most 1."
            )

        if minimum_pages < 1:
            raise ValueError("minimum_pages must be at least 1.")

        cleaned_pages = [cls.clean_text(page) for page in pages]

        if len(cleaned_pages) < minimum_pages:
            return cleaned_pages

        repeated_headers = cls._find_repeated_margin_lines(
            cleaned_pages,
            position="first",
            repetition_ratio=repetition_ratio,
        )
        repeated_footers = cls._find_repeated_margin_lines(
            cleaned_pages,
            position="last",
            repetition_ratio=repetition_ratio,
        )

        return [
            cls._remove_page_margins(
                page_text=page,
                repeated_headers=repeated_headers,
                repeated_footers=repeated_footers,
            )
            for page in cleaned_pages
        ]

    @staticmethod
    def _normalise_line_endings(text: str) -> str:
        """
        Convert Windows and legacy line endings to ``\\n``.
        """
        return text.replace("\r\n", "\n").replace("\r", "\n")

    @classmethod
    def _repair_hyphenated_line_breaks(cls, text: str) -> str:
        """
        Join lowercase words broken across extracted lines.

        Example
        -------
        ``"manu-\\nfacturing"`` becomes ``"manufacturing"``.
        """
        return cls._HYPHENATED_LINE_BREAK_PATTERN.sub("", text)

    @classmethod
    def _normalise_horizontal_whitespace(cls, text: str) -> str:
        """
        Collapse repeated spaces and tabs without removing newlines.
        """
        return cls._HORIZONTAL_WHITESPACE_PATTERN.sub(" ", text)

    @classmethod
    def _clean_individual_lines(cls, lines: list[str]) -> list[str]:
        """
        Clean each line while preserving its original order.

        Standalone page-number lines are removed. Common bullet symbols are
        converted into a consistent hyphen representation.
        """
        cleaned_lines: list[str] = []

        for line in lines:
            stripped_line = line.strip()

            if not stripped_line:
                cleaned_lines.append("")
                continue

            if cls._is_standalone_page_number(stripped_line):
                continue

            normalised_line = cls._normalise_bullet(stripped_line)
            cleaned_lines.append(normalised_line)

        return cleaned_lines

    @classmethod
    def _is_standalone_page_number(cls, line: str) -> bool:
        """
        Return whether a line contains only page-number information.
        """
        return bool(cls._PAGE_NUMBER_PATTERN.fullmatch(line))

    @classmethod
    def _normalise_bullet(cls, line: str) -> str:
        """
        Convert common Unicode bullet characters to ``"- "``.

        Existing numbered and hyphenated lists remain unchanged.
        """
        if cls._BULLET_PATTERN.match(line):
            bullet_content = cls._BULLET_PATTERN.sub("", line).strip()
            return f"- {bullet_content}" if bullet_content else "-"

        return line

    @classmethod
    def _merge_wrapped_lines(cls, lines: list[str]) -> list[str]:
        """
        Conservatively merge lines that appear to be one wrapped sentence.

        A line is merged with the following line only when:

        - neither line is empty
        - the current line does not end with terminal punctuation
        - neither line appears to be a list item
        - neither line appears to be a numbered heading
        - the following line begins with a lowercase character

        Requiring a lowercase continuation protects headings such as
        ``"Risk Assessment"`` from being incorrectly joined to body text.
        """
        if not lines:
            return []

        merged_lines: list[str] = []
        index = 0

        while index < len(lines):
            current_line = lines[index]

            if not current_line:
                merged_lines.append("")
                index += 1
                continue

            while index + 1 < len(lines):
                next_line = lines[index + 1]

                if not cls._should_merge_lines(current_line, next_line):
                    break

                current_line = f"{current_line} {next_line}".strip()
                index += 1

            merged_lines.append(current_line)
            index += 1

        return merged_lines

    @classmethod
    def _should_merge_lines(
        cls,
        current_line: str,
        next_line: str,
    ) -> bool:
        """
        Determine whether two adjacent lines are likely one wrapped sentence.
        """
        if not current_line or not next_line:
            return False

        if current_line.endswith(cls._TERMINAL_PUNCTUATION):
            return False

        if cls._LIST_ITEM_PATTERN.match(current_line):
            return False

        if cls._LIST_ITEM_PATTERN.match(next_line):
            return False

        if cls._NUMBERED_HEADING_PATTERN.match(current_line):
            return False

        if cls._NUMBERED_HEADING_PATTERN.match(next_line):
            return False

        # Only merge when the continuation begins with lowercase text.
        # This is deliberately cautious to preserve possible headings.
        return next_line[0].islower()

    @classmethod
    def _remove_excessive_blank_lines(cls, text: str) -> str:
        """
        Reduce three or more consecutive line breaks to two.
        """
        return cls._EXCESSIVE_NEWLINES_PATTERN.sub("\n\n", text)

    @classmethod
    def _find_repeated_margin_lines(
        cls,
        pages: list[str],
        position: str,
        repetition_ratio: float,
    ) -> set[str]:
        """
        Find repeated first or last non-empty page lines.

        Parameters
        ----------
        pages:
            Cleaned PDF page texts.

        position:
            Either ``"first"`` for headers or ``"last"`` for footers.

        repetition_ratio:
            Required fraction of eligible pages containing the candidate.

        Returns
        -------
        set[str]
            Normalised lines identified as repeated margin content.
        """
        if position not in {"first", "last"}:
            raise ValueError("position must be either 'first' or 'last'.")

        candidates: list[str] = []

        for page in pages:
            non_empty_lines = [
                line.strip()
                for line in page.splitlines()
                if line.strip()
            ]

            if not non_empty_lines:
                continue

            candidate = (
                non_empty_lines[0]
                if position == "first"
                else non_empty_lines[-1]
            )
            candidates.append(cls._normalise_margin_candidate(candidate))

        if not candidates:
            return set()

        occurrence_counts = Counter(candidates)
        required_occurrences = max(
            2,
            int(len(candidates) * repetition_ratio + 0.999),
        )

        return {
            line
            for line, count in occurrence_counts.items()
            if line and count >= required_occurrences
        }

    @staticmethod
    def _normalise_margin_candidate(line: str) -> str:
        """
        Normalise a margin line before comparing it across pages.

        Digits are replaced so headers such as revision dates or numbered
        references can still be recognised as a repeating pattern.
        """
        normalised = line.casefold().strip()
        normalised = re.sub(r"\d+", "<number>", normalised)
        normalised = re.sub(r"\s+", " ", normalised)

        return normalised

    @classmethod
    def _remove_page_margins(
        cls,
        page_text: str,
        repeated_headers: set[str],
        repeated_footers: set[str],
    ) -> str:
        """
        Remove identified repeated header and footer lines from one page.
        """
        lines = page_text.splitlines()

        non_empty_indexes = [
            index
            for index, line in enumerate(lines)
            if line.strip()
        ]

        if not non_empty_indexes:
            return ""

        first_index = non_empty_indexes[0]
        last_index = non_empty_indexes[-1]

        first_candidate = cls._normalise_margin_candidate(
            lines[first_index]
        )
        last_candidate = cls._normalise_margin_candidate(
            lines[last_index]
        )

        if first_candidate in repeated_headers:
            lines[first_index] = ""

        if last_candidate in repeated_footers:
            lines[last_index] = ""

        cleaned = "\n".join(lines)
        cleaned = cls._remove_excessive_blank_lines(cleaned)

        return cleaned.strip()