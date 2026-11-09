#!/usr/bin/env python3
"""Audit that a Spanish book was translated from the TR, not another text.

Read-only. Never writes STATUS.md, never writes a state, never writes `ready`
or `done`. It reports; you decide.

    python3 tools/audit_tr.py filipenses
    python3 tools/audit_tr.py            # every NT book with a translation file

What this can and cannot do
---------------------------
It cannot judge whether a rendering is good. It checks one narrow question:
does the Spanish carry the readings of the Textus Receptus in
`source/greek/TR1894/`, or does it carry the readings of some other text?

Four mechanical checks derive entirely from the TR files already in this
repository, so they need no maintenance and no second Greek edition:

  inventory   every TR verse has a Spanish verse, and no extras
  names       proper nouns and place names in the TR appear in the Spanish
  order       adjacent Ihsou/Cristou pairs keep the TR's order and approved
              distinct Spanish forms
  brevity     a verse far shorter than its neighbours may have dropped a
              clause the TR has and the critical text lacks

One curated check reads `tools/tr-divergences/{book}.json`: hand-recorded
places where the TR and the critical text genuinely differ, each with a test
on the Spanish. Mechanical checks catch omissions and order flips. The
registry is what catches same-length swaps.

The report ends with a coverage line stating how many verses no check
touched. A verse this script did not examine is not a verse it approved.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from statistics import median

import status as lbf

ROOT = lbf.ROOT
REGISTRY_DIR = ROOT / "tools" / "tr-divergences"
GREEK_DIR = ROOT / "source" / "greek" / "TR1894" / "robinson-parsed"

# NT book slug -> Robinson parsed filename stem.
UTR_CODE = {
    "mateo": "MT", "marcos": "MR", "lucas": "LU", "juan": "JOH",
    "hechos": "AC", "romanos": "RO", "1corintios": "1CO", "2corintios": "2CO",
    "galatas": "GA", "efesios": "EPH", "filipenses": "PHP", "colosenses": "COL",
    "1tesalonicenses": "1TH", "2tesalonicenses": "2TH", "1timoteo": "1TI",
    "2timoteo": "2TI", "titus": "TIT", "filemon": "PHM", "hebreos": "HEB",
    "santiago": "JAS", "1pedro": "1PE", "2pedro": "2PE", "1juan": "1JO",
    "2juan": "2JO", "3juan": "3JO", "judas": "JUDE", "apocalipsis": "RE",
}

STRONG_IESOUS = "2424"
STRONG_CHRISTOS = "5547"

# Strong's -> Spanish pattern, for words whose rendering is effectively forced.
# Only proper nouns, place names and gentilics belong here. A general gloss
# table would produce noise, and noise is how a checker gets ignored.
NAMES = {
    "3972": r"pablo", "5095": r"timoteo", "5375": r"filipos",
    "5374": r"filipens", "1891": r"epafrodito", "2136": r"evodia",
    "4941": r"sintique", "2815": r"clemente", "2332": r"tesalonica",
    "3109": r"macedonia", "2541": r"cesar", "2474": r"israel",
    "958": r"benjamin", "1445": r"hebre", "5330": r"farise",
    "4232": r"pretorio", "5103": r"tito", "2914": r"creta",
    "2912": r"cretens", "736": r"artemas", "5190": r"tiquico",
    "3533": r"nicopolis", "2211": r"zenas", "625": r"apolo",
    "281": r"amen", "2424": r"jesus", "5547": r"crist",
    "4074": r"pedro", "3110": r"macedon", "882": r"acaya",
    "4613": r"silvano",
}

VERSE_LINE = re.compile(r"^(\d+):(\d+)\s+(.*)$")
TOKEN = re.compile(r"([^{}]*)\{([^}]*)\}")


# ---------------------------------------------------------------- utilities

def fold(text: str) -> str:
    """Lowercase and strip accents, so patterns can be written accent-free."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


class Finding:
    __slots__ = ("ref", "check", "severity", "message")

    def __init__(self, ref: str, check: str, severity: str, message: str):
        self.ref = ref
        self.check = check
        self.severity = severity
        self.message = message


# ------------------------------------------------------------- greek source

def parse_utr(path: Path) -> dict[tuple[int, int], list[dict]]:
    """Parse a Robinson .UTR file into {(chapter, verse): [token, ...]}.

    A token chunk looks like `word 1234 5678 {V-PAI-1S}`. Where Robinson
    records a variant the surface forms are pipe-separated before the
    Strong's number: `| idete | eidete | 3708 5627 {V-2AAI-2P}`. Both forms
    are kept; a Spanish rendering matching either one is accepted.
    """
    verses: dict[tuple[int, int], list[dict]] = {}
    current: tuple[int, int] | None = None
    buffer: list[str] = []

    def flush() -> None:
        if current is None:
            return
        body = " ".join(buffer)
        tokens: list[dict] = []
        # Robinson brackets the scribal subscription, opening on the first of
        # its tokens and closing on the last. Everything between is subscript
        # too, so carry the state across tokens rather than testing each one.
        in_subscript = False
        for chunk, morph in TOKEN.findall(body):
            opened = "[" in chunk
            closed = "]" in chunk
            subscript = in_subscript or opened
            if opened and not closed:
                in_subscript = True
            elif closed:
                in_subscript = False
            words = chunk.replace("|", " ").split()
            strongs = []
            surfaces = []
            for word in words:
                if word.isdigit():
                    strongs.append(word)
                else:
                    surfaces.append(word.strip("[]"))
            if not surfaces and not strongs:
                continue
            tokens.append(
                {
                    "surfaces": surfaces,
                    "strong": strongs[0] if strongs else "",
                    "morph": morph,
                    "subscript": subscript,
                }
            )
        verses[current] = tokens

    for line in path.read_text(encoding="utf-8").splitlines():
        match = VERSE_LINE.match(line)
        if match:
            flush()
            current = (int(match.group(1)), int(match.group(2)))
            buffer = [match.group(3)]
        elif current is not None and line.strip():
            buffer.append(line.strip())
    flush()
    return verses


# ----------------------------------------------------------------- registry

def load_registry(book: str) -> tuple[list[dict], str | None]:
    path = REGISTRY_DIR / f"{book}.json"
    if not path.is_file():
        return [], None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("points") or [], str(path.relative_to(ROOT))


# ------------------------------------------------------------------- checks

def check_inventory(greek, spanish, findings: list[Finding]) -> None:
    missing = sorted(set(greek) - set(spanish))
    extra = sorted(set(spanish) - set(greek))
    for ch, vs in missing:
        findings.append(
            Finding(f"{ch}:{vs}", "inventory", "FAIL", "TR has this verse; the Spanish does not")
        )
    for ch, vs in extra:
        findings.append(
            Finding(f"{ch}:{vs}", "inventory", "FAIL", "Spanish has this verse; the TR does not")
        )


def check_names(greek, spanish, findings: list[Finding], touched: set) -> int:
    unmapped: set[str] = set()
    for key in sorted(set(greek) & set(spanish)):
        text = fold(spanish[key])
        for token in greek[key]:
            if token["subscript"]:
                continue
            strong = token["strong"]
            is_proper = token["morph"] == "N-PRI"
            pattern = NAMES.get(strong)
            if pattern is None:
                if is_proper:
                    unmapped.add(f"{strong} ({'/'.join(token['surfaces'])})")
                continue
            touched.add(key)
            if not re.search(pattern, text):
                findings.append(
                    Finding(
                        f"{key[0]}:{key[1]}",
                        "names",
                        "FAIL",
                        f"TR has {'/'.join(token['surfaces'])} (Strong {strong}); "
                        f"no /{pattern}/ in the Spanish",
                    )
                )
    for item in sorted(unmapped):
        findings.append(
            Finding("-", "names", "SKIP", f"proper noun {item} has no entry in NAMES; not checked")
        )
    return len(unmapped)


def check_name_order(greek, spanish, findings: list[Finding], touched: set) -> None:
    for key in sorted(set(greek) & set(spanish)):
        tokens = [t for t in greek[key] if not t["subscript"]]
        text = fold(spanish[key])
        want_jc = 0
        want_cj = 0
        for a, b in zip(tokens, tokens[1:]):
            if a["strong"] == STRONG_IESOUS and b["strong"] == STRONG_CHRISTOS:
                want_jc += 1
            elif a["strong"] == STRONG_CHRISTOS and b["strong"] == STRONG_IESOUS:
                want_cj += 1
        if not (want_jc or want_cj):
            continue
        touched.add(key)
        approved_jc = len(re.findall(r"\bjesus\s*,\s*\*el\*\s+crist\w*\b", text))
        bare_jc = len(re.findall(r"\bjesus\s+crist\w*\b", text))
        fused_jc = len(re.findall(r"\bjesucrist\w*\b", text))
        got_jc = approved_jc + bare_jc + fused_jc
        got_cj = len(re.findall(r"crist\w*\s+jesus", text))
        if fused_jc:
            findings.append(
                Finding(
                    f"{key[0]}:{key[1]}",
                    "order",
                    "FAIL",
                    "LPF keeps Jesus and Cristo as distinct tokens; replace «Jesucristo» with the approved ordered form",
                )
            )
        if bare_jc:
            findings.append(
                Finding(
                    f"{key[0]}:{key[1]}",
                    "order",
                    "FAIL",
                    "LPF renders Ihsou Cristou as «Jesús, *el* Cristo», not «Jesús Cristo»",
                )
            )
        if got_jc < want_jc and got_cj > want_cj:
            findings.append(
                Finding(
                    f"{key[0]}:{key[1]}",
                    "order",
                    "FAIL",
                    f"TR reads Ihsou Cristou ({want_jc}x) but the Spanish reads «Cristo Jesús»",
                )
            )
        elif got_cj < want_cj and got_jc > want_jc:
            findings.append(
                Finding(
                    f"{key[0]}:{key[1]}",
                    "order",
                    "FAIL",
                    f"TR reads Cristou Ihsou ({want_cj}x) but the Spanish uses the Jesus-Christ order",
                )
            )
        elif got_jc + got_cj < want_jc + want_cj:
            findings.append(
                Finding(
                    f"{key[0]}:{key[1]}",
                    "order",
                    "REVIEW",
                    f"TR has {want_jc + want_cj} Jesus/Cristo pair(s); "
                    f"the Spanish shows {got_jc + got_cj}",
                )
            )


def check_brevity(greek, spanish, findings: list[Finding]) -> None:
    """Flag verses far shorter than the book's own norm.

    The critical text is usually the shorter text, so a Spanish verse that is
    unusually short for its Greek is a candidate for a dropped TR clause. This
    is statistical. It reports candidates, never failures.
    """
    ratios: dict[tuple[int, int], float] = {}
    for key in sorted(set(greek) & set(spanish)):
        n_greek = len([t for t in greek[key] if not t["subscript"]])
        n_spanish = len(spanish[key].split())
        if n_greek >= 5:
            ratios[key] = n_spanish / n_greek
    if len(ratios) < 10:
        return
    values = sorted(ratios.values())
    mid = median(values)
    spread = median([abs(v - mid) for v in values]) or 0.01
    for key, ratio in sorted(ratios.items()):
        if ratio < mid - 3 * spread:
            findings.append(
                Finding(
                    f"{key[0]}:{key[1]}",
                    "brevity",
                    "REVIEW",
                    f"Spanish/Greek word ratio {ratio:.2f} vs book median {mid:.2f}; "
                    "check for a dropped TR clause",
                )
            )


def check_registry(points, spanish, findings: list[Finding], touched: set) -> None:
    for point in points:
        ref = str(point.get("ref") or "")
        match = re.match(r"(\d+):(\d+)$", ref)
        if not match:
            findings.append(Finding(ref or "-", "registry", "FAIL", "entry has no usable ref"))
            continue
        key = (int(match.group(1)), int(match.group(2)))
        if key not in spanish:
            findings.append(Finding(ref, "registry", "FAIL", "registry names a verse the Spanish lacks"))
            continue
        touched.add(key)
        text = fold(spanish[key])
        note = str(point.get("note") or "")
        must = point.get("must_match")
        must_not = point.get("must_not_match")
        if must and not re.search(must, text):
            findings.append(
                Finding(ref, "registry", "FAIL", f"expected /{must}/ for the TR reading — {note}")
            )
        if must_not and re.search(must_not, text):
            findings.append(
                Finding(ref, "registry", "FAIL", f"found /{must_not}/, a non-TR reading — {note}")
            )


# -------------------------------------------------------------------- report

def audit(book: str, testament: str) -> tuple[int, int]:
    """Return (fail_count, review_count). Prints the report."""
    code = UTR_CODE.get(book)
    t_path = lbf.translation_path(book, testament)
    print(f"\n=== {book} ===")
    if code is None:
        print("  not a NT book; the TR audit does not apply")
        return 0, 0
    g_path = GREEK_DIR / f"{code}.UTR"
    if not g_path.is_file():
        print(f"  TR source missing: {g_path.relative_to(ROOT)}")
        return 1, 0
    if not t_path.is_file():
        print("  no translation file")
        return 0, 0

    greek = parse_utr(g_path)
    spanish = lbf.parse_verses(t_path)
    points, registry_path = load_registry(book)

    findings: list[Finding] = []
    touched: set = set()
    check_inventory(greek, spanish, findings)
    unmapped = check_names(greek, spanish, findings, touched)
    check_name_order(greek, spanish, findings, touched)
    check_brevity(greek, spanish, findings)
    check_registry(points, spanish, findings, touched)

    order = {"FAIL": 0, "REVIEW": 1, "SKIP": 2}
    findings.sort(key=lambda f: (order[f.severity], f.ref))

    fails = sum(1 for f in findings if f.severity == "FAIL")
    reviews = sum(1 for f in findings if f.severity == "REVIEW")

    print(f"  TR source     {g_path.relative_to(ROOT)}")
    print(f"  Spanish       {t_path.relative_to(ROOT)}  ({len(spanish)} verses)")
    print(f"  registry      {registry_path or 'none — mechanical checks only'} "
          f"({len(points)} divergence point(s))")
    print()

    if not findings:
        print("  no findings")
    for f in findings:
        print(f"  {f.severity:<6} {f.ref:<8} {f.check:<9} {f.message}")

    shared = set(greek) & set(spanish)
    untouched = len(shared) - len(touched & shared)
    print()
    print(f"  coverage: {len(touched & shared)}/{len(shared)} verses examined by at least one "
          f"check; {untouched} verse(s) no check touched.")
    if unmapped:
        print(f"            {unmapped} proper noun(s) had no gloss and were skipped.")
    print("            A verse this script did not examine is not a verse it approved.")
    return fails, reviews


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("book", nargs="?", help="One book slug. Default: every NT book with a file.")
    args = parser.parse_args()

    rows = lbf.parse_status_table(lbf.STATUS_PATH.read_text(encoding="utf-8"))
    if args.book:
        rows = [r for r in rows if r["book"] == args.book]
        if not rows:
            print(f"{args.book} is not in STATUS.md", file=sys.stderr)
            return 2

    total_fail = 0
    total_review = 0
    seen = 0
    for row in rows:
        if row["testament"] != "nt":
            continue
        if not lbf.translation_path(row["book"], row["testament"]).is_file():
            continue
        seen += 1
        fails, reviews = audit(row["book"], row["testament"])
        total_fail += fails
        total_review += reviews

    print()
    print("=" * 60)
    print(f"{seen} book(s) audited: {total_fail} FAIL, {total_review} REVIEW")
    print("This script writes nothing. `ready` is still verify.py's to write,")
    print("and `done` is still yours.")
    return 1 if total_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
