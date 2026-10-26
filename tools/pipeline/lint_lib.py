"""Cheap local checks before an audit. No API. Never writes translation/*.md."""

from __future__ import annotations

import re
from pathlib import Path

from books import ROOT, get_book

RULES = (
    (re.compile(r"\b(?:Jehová|Jehova|Yahweh|Yahveh|Yavé|Yave|YHWH)\b", re.I), "יהוה must be rendered Yahvé"),
    (re.compile(r"\bvosotros\b", re.I), "Spain vosotros"),
    (re.compile(r"\bvosotras\b", re.I), "Spain vosotras"),
    (re.compile(r"\b(?:hagáis|haréis|habéis|tenéis|veréis|veáis|asistáis|mataréis)\b", re.I), "Spain 2pl verb"),
    (re.compile(r"\bmatad(?:lo|la|los|las)?\b", re.I), "Spain imperative matad"),
    (
        re.compile(
            r"\b(?:parir(?:[áé](?:is|n|s|mos)?)?|parió|parieron|pariendo|parís|parid)\b",
            re.I,
        ),
        "archaic parir",
    ),
    (re.compile(r"\bque viva\b", re.I), "jussive que viva; qal is vivirá"),
    (re.compile(r"\bel sexo\b", re.I), "el sexo is not in the packet; gender is si hijo / si hija"),
    (re.compile(r"entre las piernas", re.I), "entre las piernas interprets dual stones"),
    (re.compile(r"\b(?:el|sus|los) partos?\b", re.I), "extra noun parto"),
    (re.compile(r"asiento de piedra|birthstool", re.I), "dual stones are not a stool"),
    (re.compile(r"den a luz a las hebreas", re.I), "addressees giving birth to the Hebrew women"),
    (
        re.compile(r"^(?:Y\s+)?(?:Él|Ella),\s+[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÜÑáéíóúüñ-]+\s+y\s+[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÜÑáéíóúüñ-]+(?:,|\s)", re.UNICODE),
        "incomplete Spanish identification: a pronoun followed by coordinated names needs a grammatical predicate",
    ),
)


def lint_path(slug: str, chapter: int, verse: int) -> Path:
    book = get_book(slug)
    return (
        ROOT
        / "pipeline"
        / book.testament
        / book.slug
        / f"{book.slug}-{chapter}-{verse}.lint.json"
    )


def lint_spanish(spanish: str) -> list[dict]:
    text = spanish or ""
    findings = []
    seen = set()
    if "**" in text:
        findings.append({
            "severity": "fail",
            "sourceTokenIds": [],
            "issue": "Supplied words use single Markdown asterisks, not bold markup",
            "spanishSpan": "**",
        })
    without_supplied = re.sub(r"(?<!\*)\*[^*\n]+\*(?!\*)", "", text)
    if "*" in without_supplied:
        findings.append({
            "severity": "fail",
            "sourceTokenIds": [],
            "issue": "Unbalanced supplied-word italics",
            "spanishSpan": "*",
        })
    for pattern, issue in RULES:
        match = pattern.search(text)
        if not match or issue in seen:
            continue
        seen.add(issue)
        findings.append(
            {
                "severity": "fail",
                "sourceTokenIds": [],
                "issue": issue,
                "spanishSpan": match.group(0),
            }
        )
    return findings


def lint_divine_name(spanish: str, packet: dict) -> list[dict]:
    """Require one locked `Yahvé` for each explicit יהוה token."""
    ids = [
        str(token.get("sourceTokenId"))
        for token in packet.get("tokens") or []
        if re.search(r"(?:^|/)3068(?:\s|$)", str(token.get("lemma") or ""))
    ]
    if not ids:
        return []
    found = len(re.findall(r"\bYahvé\b", spanish or "", re.I))
    if found == len(ids):
        return []
    return [{
        "severity": "fail",
        "sourceTokenIds": ids,
        "issue": f"Every explicit יהוה must be rendered Yahvé (expected {len(ids)}, found {found})",
        "spanishSpan": "Yahvé" if found else "",
    }]
