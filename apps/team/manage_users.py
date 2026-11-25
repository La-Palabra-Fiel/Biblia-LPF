#!/usr/bin/env python3
"""Manage Team Desk reviewer credentials without storing plaintext secrets."""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import desk  # noqa: E402


def save_people(people: dict[str, str]) -> None:
    desk.secure_private_storage()
    desk.write_json(desk.PEOPLE, dict(sorted(people.items(), key=lambda item: item[0].casefold())))
    try:
        desk.PEOPLE.chmod(0o600)
    except OSError:
        pass


def add_user(name: str) -> None:
    person = desk.clean_name(name)
    people = desk.load_people()
    existing = next((known for known in people if known.casefold() == person.casefold()), None)
    if existing:
        answer = input(f"Replace the credential for {existing}? [y/N] ").strip().casefold()
        if answer != "y":
            raise SystemExit("No change made.")
        person = existing
    first = getpass.getpass("New reviewer credential (12+ characters): ")
    second = getpass.getpass("Repeat credential: ")
    if first != second:
        raise SystemExit("Credentials did not match.")
    people[person] = desk.hashed_credential(first)
    save_people(people)
    print(f"Saved hashed credential for {person} in {desk.PEOPLE}")


def migrate_users() -> None:
    people = desk.load_people()
    plain = [name for name, value in people.items() if not desk.credential_is_hashed(value)]
    if not plain:
        print("All reviewer credentials are already hashed.")
        return
    print("This converts the existing credentials in place. Reviewers keep their current credentials.")
    if input(f"Hash {len(plain)} plaintext credential(s)? [y/N] ").strip().casefold() != "y":
        raise SystemExit("No change made.")
    for name in plain:
        # Migration is the sole exception to the new-secret length rule: it
        # removes existing plaintext immediately without silently changing a
        # reviewer's credential. Rotate short legacy credentials afterwards.
        value = people[name]
        salt_record = desk.hashed_credential(value) if len(value) >= 12 else _hash_legacy(value)
        people[name] = salt_record
    save_people(people)
    print(f"Converted {len(plain)} credential(s). Rotate any legacy short credentials before production use.")


def _hash_legacy(secret: str) -> str:
    """Hash a short legacy value only during explicit in-place migration."""
    import base64
    import hashlib
    import secrets

    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(secret.encode("utf-8"), salt=salt, n=desk.SCRYPT_N, r=desk.SCRYPT_R, p=desk.SCRYPT_P, dklen=32)
    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    encoded_digest = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"scrypt${desk.SCRYPT_N}${desk.SCRYPT_R}${desk.SCRYPT_P}${encoded_salt}${encoded_digest}"


def list_users() -> None:
    people = desk.load_people()
    for name, value in sorted(people.items(), key=lambda item: item[0].casefold()):
        print(f"{name}\t{'hashed' if desk.credential_is_hashed(value) else 'PLAINTEXT — migrate before production'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    add = subcommands.add_parser("add", help="add or rotate one reviewer")
    add.add_argument("name")
    subcommands.add_parser("migrate", help="hash existing plaintext credentials in place")
    subcommands.add_parser("list", help="list names and credential storage state")
    args = parser.parse_args()
    if args.command == "add":
        add_user(args.name)
    elif args.command == "migrate":
        migrate_users()
    else:
        list_users()


if __name__ == "__main__":
    main()
