
"""Shared multilingual tokenizer for RankEngine.

Uses Unicode normalization and character bigrams for Japanese/CJK text.
This is a dictionary-free approximation, not linguistic word segmentation.
"""

import re
import unicodedata


_CJK_CLASS = (
    "\u3040-\u30ff"
    "\u3400-\u4dbf"
    "\u4e00-\u9fff"
    "\uf900-\ufaff"
)

_TOKEN_PATTERN = re.compile(
    rf"[{_CJK_CLASS}]+|[^\W_{_CJK_CLASS}]+",
    flags=re.UNICODE,
)

_CJK_RUN = re.compile(rf"^[{_CJK_CLASS}]+$")


def normalize(text: object) -> str:
    """Normalize Unicode text and lowercase it."""
    if not isinstance(text, str):
        return ""
    return unicodedata.normalize("NFKC", text).lower()


def tokenize(text: object) -> list[str]:
    """Tokenize ordinary words and Japanese/CJK character bigrams."""
    tokens: list[str] = []

    for piece in _TOKEN_PATTERN.findall(normalize(text)):
        if _CJK_RUN.fullmatch(piece):
            if len(piece) == 1:
                tokens.append(piece)
            else:
                tokens.extend(
                    piece[index:index + 2]
                    for index in range(len(piece) - 1)
                )
        else:
            tokens.append(piece)

    return tokens


if __name__ == "__main__":
    checks = [
        ("Zapatillas Nike", ["zapatillas", "nike"]),
        ("ＡＢＣ 15", ["abc", "15"]),
        (
            "ノートパソコン",
            ["ノー", "ート", "トパ", "パソ", "ソコ", "コン"],
        ),
        ("猫", ["猫"]),
        ("15インチ", ["15", "イン", "ンチ"]),
        ("", []),
        (None, []),
    ]

    failed = 0

    for sample, expected in checks:
        actual = tokenize(sample)
        passed = actual == expected
        print(
            ("PASS" if passed else "FAIL"),
            repr(sample),
            "->",
            actual,
        )
        if not passed:
            failed += 1

    if failed:
        raise SystemExit(f"{failed} tokenizer check(s) failed")

    print("All tokenizer checks passed.")
