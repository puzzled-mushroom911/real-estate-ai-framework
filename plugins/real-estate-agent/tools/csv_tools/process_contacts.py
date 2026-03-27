#!/usr/bin/env python3
"""
Process and clean contact CSV files for CRM import.

Normalizes phone numbers, validates emails, deduplicates records,
standardizes names, and flags incomplete entries.

Usage:
    python3 process_contacts.py <input.csv> [options]

Examples:
    python3 process_contacts.py leads.csv
    python3 process_contacts.py leads.csv --output cleaned.csv --dedupe
    python3 process_contacts.py leads.csv --validate-phones --validate-emails
    python3 process_contacts.py leads.csv --dedupe --validate-phones --validate-emails
"""

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PHONE_STRIP_CHARS = re.compile(r"[^\d+]")
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
US_PHONE_PATTERN = re.compile(r"^1?\d{10}$")

# Fields that must be present for a record to be considered complete
REQUIRED_FIELDS = {"first_name", "last_name", "email", "phone"}

# Common CSV column name aliases mapped to canonical names
COLUMN_ALIASES: Dict[str, str] = {
    "firstname": "first_name",
    "first name": "first_name",
    "first": "first_name",
    "lastname": "last_name",
    "last name": "last_name",
    "last": "last_name",
    "email address": "email",
    "email_address": "email",
    "phone number": "phone",
    "phone_number": "phone",
    "mobile": "phone",
    "cell": "phone",
    "telephone": "phone",
}


# ---------------------------------------------------------------------------
# Cleaning functions
# ---------------------------------------------------------------------------
def normalize_column_names(headers: List[str]) -> List[str]:
    """Map common column name variants to canonical names."""
    normalized = []
    for h in headers:
        key = h.strip().lower().replace("-", "_")
        canonical = COLUMN_ALIASES.get(key, key)
        normalized.append(canonical)
    return normalized


def normalize_phone(phone: str) -> Tuple[str, bool]:
    """
    Strip non-digit characters, add US country code, validate format.

    Returns:
        Tuple of (cleaned_phone, is_valid).
    """
    if not phone or not phone.strip():
        return ("", False)

    digits = PHONE_STRIP_CHARS.sub("", phone.strip())

    # Remove leading + if present (we already stripped it from digits)
    digits = digits.lstrip("+")

    # Add country code if 10 digits (US)
    if len(digits) == 10:
        digits = "1" + digits

    is_valid = bool(US_PHONE_PATTERN.match(digits))
    formatted = f"+{digits}" if is_valid else digits
    return (formatted, is_valid)


def validate_email(email: str) -> bool:
    """Check whether an email address matches a valid format."""
    if not email or not email.strip():
        return False
    return bool(EMAIL_PATTERN.match(email.strip().lower()))


def standardize_name(name: str) -> str:
    """Convert a name to proper title case, handling edge cases."""
    if not name or not name.strip():
        return ""
    # title() then fix common particles
    result = name.strip().title()
    for particle in ("Mc", "Mac", "O'"):
        # e.g., Mcdonald -> McDonald
        idx = result.find(particle)
        if idx >= 0 and len(result) > idx + len(particle):
            next_char_pos = idx + len(particle)
            result = result[:next_char_pos] + result[next_char_pos].upper() + result[next_char_pos + 1:]
    return result


def is_incomplete(row: Dict[str, str]) -> bool:
    """Return True if any required field is empty or missing."""
    for field in REQUIRED_FIELDS:
        if not row.get(field, "").strip():
            return True
    return False


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------
def process_contacts(
    input_path: Path,
    output_path: Path,
    dedupe: bool = False,
    validate_phones: bool = False,
    validate_emails: bool = False,
) -> Dict[str, int]:
    """
    Read a contact CSV, clean it, and write the result.

    Args:
        input_path: Path to the source CSV.
        output_path: Path for the cleaned output CSV.
        dedupe: Remove duplicate records by email or phone.
        validate_phones: Normalize and validate phone numbers.
        validate_emails: Validate email format and flag invalid.

    Returns:
        Dict with processing statistics.
    """
    stats = {
        "total_input": 0,
        "total_output": 0,
        "duplicates_removed": 0,
        "invalid_phones": 0,
        "invalid_emails": 0,
        "incomplete_flagged": 0,
        "names_standardized": 0,
    }

    # Read all rows
    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        raw_headers = list(reader.fieldnames or [])
        canonical_headers = normalize_column_names(raw_headers)

        rows: List[Dict[str, str]] = []
        for raw_row in reader:
            # Re-key using canonical names
            row = {canonical_headers[i]: v for i, (_, v) in enumerate(raw_row.items())}
            rows.append(row)

    stats["total_input"] = len(rows)
    print(f"Read {stats['total_input']} rows from {input_path.name}")

    # --- Standardize names ---
    for row in rows:
        for field in ("first_name", "last_name"):
            original = row.get(field, "")
            cleaned = standardize_name(original)
            if cleaned != original:
                stats["names_standardized"] += 1
            row[field] = cleaned

    # --- Validate and normalize phones ---
    if validate_phones:
        for row in rows:
            raw_phone = row.get("phone", "")
            cleaned_phone, is_valid = normalize_phone(raw_phone)
            row["phone"] = cleaned_phone
            if raw_phone.strip() and not is_valid:
                stats["invalid_phones"] += 1
                row.setdefault("_flags", "")
                row["_flags"] += "invalid_phone;"

    # --- Validate emails ---
    if validate_emails:
        for row in rows:
            raw_email = row.get("email", "").strip().lower()
            row["email"] = raw_email
            if raw_email and not validate_email(raw_email):
                stats["invalid_emails"] += 1
                row.setdefault("_flags", "")
                row["_flags"] += "invalid_email;"

    # --- Flag incomplete records ---
    for row in rows:
        if is_incomplete(row):
            stats["incomplete_flagged"] += 1
            row.setdefault("_flags", "")
            row["_flags"] += "incomplete;"

    # --- Deduplicate ---
    if dedupe:
        seen_emails: set[str] = set()
        seen_phones: set[str] = set()
        unique_rows: List[Dict[str, str]] = []
        for row in rows:
            email = row.get("email", "").strip().lower()
            phone = row.get("phone", "").strip()

            is_dupe = False
            if email and email in seen_emails:
                is_dupe = True
            if phone and phone in seen_phones:
                is_dupe = True

            if is_dupe:
                stats["duplicates_removed"] += 1
                continue

            if email:
                seen_emails.add(email)
            if phone:
                seen_phones.add(phone)
            unique_rows.append(row)
        rows = unique_rows

    stats["total_output"] = len(rows)

    # --- Write output ---
    if not rows:
        print("Warning: no rows to write after processing.")
        return stats

    # Build output headers: canonical + _flags if any rows have flags
    output_headers = [h for h in canonical_headers if h in rows[0]]
    has_flags = any(row.get("_flags") for row in rows)
    if has_flags and "_flags" not in output_headers:
        output_headers.append("_flags")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    return stats


def print_summary(stats: Dict[str, int]) -> None:
    """Print a human-readable processing summary."""
    print("\n" + "=" * 60)
    print("CONTACT PROCESSING SUMMARY")
    print("=" * 60)
    print(f"  Total input rows       : {stats['total_input']}")
    print(f"  Total output rows      : {stats['total_output']}")
    print(f"  Duplicates removed     : {stats['duplicates_removed']}")
    print(f"  Invalid phones flagged : {stats['invalid_phones']}")
    print(f"  Invalid emails flagged : {stats['invalid_emails']}")
    print(f"  Incomplete records     : {stats['incomplete_flagged']}")
    print(f"  Names standardized     : {stats['names_standardized']}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process and clean contact CSV files for CRM import.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 process_contacts.py leads.csv\n"
            "  python3 process_contacts.py leads.csv --output cleaned.csv --dedupe\n"
            "  python3 process_contacts.py leads.csv --validate-phones --validate-emails\n"
        ),
    )
    parser.add_argument("input_csv", help="Path to the input CSV file")
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output CSV path (default: <input>_cleaned.csv)",
    )
    parser.add_argument(
        "--dedupe",
        action="store_true",
        help="Remove duplicate contacts by email or phone",
    )
    parser.add_argument(
        "--validate-phones",
        action="store_true",
        help="Normalize and validate phone numbers",
    )
    parser.add_argument(
        "--validate-emails",
        action="store_true",
        help="Validate email address format",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    input_path = Path(args.input_csv)
    if not input_path.exists():
        print(f"Error: file '{input_path}' does not exist.")
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_stem(input_path.stem + "_cleaned")

    stats = process_contacts(
        input_path=input_path,
        output_path=output_path,
        dedupe=args.dedupe,
        validate_phones=args.validate_phones,
        validate_emails=args.validate_emails,
    )
    print_summary(stats)
    print(f"\nCleaned file written to: {output_path}")
