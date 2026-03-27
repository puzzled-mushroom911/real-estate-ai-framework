#!/usr/bin/env python3
"""
General-purpose data cleaning utilities for real estate CSVs.

Handles address standardization, price normalization, missing data flagging,
and zip code validation.

Usage:
    python3 clean_data.py <input.csv> [options]

Examples:
    python3 clean_data.py listings.csv --fix-addresses --fix-prices
    python3 clean_data.py listings.csv --fix-addresses --fix-prices --fill-missing
    python3 clean_data.py listings.csv --output cleaned_listings.csv --fix-addresses
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

# Common street abbreviation expansions (USPS standard)
ADDRESS_ABBREVIATIONS: Dict[str, str] = {
    r"\bSt\b": "Street",
    r"\bDr\b": "Drive",
    r"\bAve\b": "Avenue",
    r"\bBlvd\b": "Boulevard",
    r"\bCt\b": "Court",
    r"\bLn\b": "Lane",
    r"\bRd\b": "Road",
    r"\bPl\b": "Place",
    r"\bPkwy\b": "Parkway",
    r"\bCir\b": "Circle",
    r"\bTrl\b": "Trail",
    r"\bWay\b": "Way",
    r"\bTer\b": "Terrace",
    r"\bHwy\b": "Highway",
    r"\bApt\b": "Apartment",
    r"\bSte\b": "Suite",
    r"\bFl\b": "Floor",
    r"\bN\b": "North",
    r"\bS\b": "South",
    r"\bE\b": "East",
    r"\bW\b": "West",
    r"\bNE\b": "Northeast",
    r"\bNW\b": "Northwest",
    r"\bSE\b": "Southeast",
    r"\bSW\b": "Southwest",
}

# US zip code pattern: 5 digits or 5+4
ZIP_PATTERN = re.compile(r"^\d{5}(-\d{4})?$")

# Price-related column names (lowercase)
PRICE_COLUMNS = {"price", "list_price", "sale_price", "sold_price", "asking_price", "close_price"}

# Address-related column names (lowercase)
ADDRESS_COLUMNS = {"address", "street_address", "property_address", "street", "full_address"}

# Zip code column names (lowercase)
ZIP_COLUMNS = {"zip", "zip_code", "zipcode", "postal_code"}

# Critical fields -- rows missing any of these get flagged
CRITICAL_FIELDS = {"address", "street_address", "property_address", "price", "list_price", "status"}


# ---------------------------------------------------------------------------
# Cleaning functions
# ---------------------------------------------------------------------------
def clean_address(address: str) -> str:
    """
    Standardize a street address: expand abbreviations and apply proper case.

    Args:
        address: Raw address string.

    Returns:
        Cleaned address string.
    """
    if not address or not address.strip():
        return address

    result = address.strip()

    # Apply proper case first (before abbreviation expansion)
    result = result.title()

    # Expand abbreviations (case-insensitive matching, replace with full word)
    for pattern, replacement in ADDRESS_ABBREVIATIONS.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    # Normalize whitespace
    result = re.sub(r"\s+", " ", result).strip()

    return result


def validate_zip(zip_code: str) -> Tuple[str, bool]:
    """
    Validate and clean a US zip code.

    Returns:
        Tuple of (cleaned_zip, is_valid).
    """
    if not zip_code or not zip_code.strip():
        return ("", False)

    cleaned = zip_code.strip()

    # Sometimes zips come as floats from Excel (e.g., "33701.0")
    if "." in cleaned:
        try:
            cleaned = str(int(float(cleaned)))
        except (ValueError, OverflowError):
            pass

    # Pad short zips (e.g., "1234" -> "01234")
    if cleaned.isdigit() and len(cleaned) < 5:
        cleaned = cleaned.zfill(5)

    is_valid = bool(ZIP_PATTERN.match(cleaned))
    return (cleaned, is_valid)


def clean_price(value: str) -> Tuple[str, bool]:
    """
    Convert a price string to a clean numeric value.

    Handles: $350,000 / 350000 / $1.2M / 1.2m / "$500K" etc.

    Returns:
        Tuple of (numeric_string, is_valid).
    """
    if not value or not value.strip():
        return ("", False)

    raw = value.strip().upper()

    # Strip currency symbols and whitespace
    raw = raw.replace("$", "").replace(",", "").strip()

    # Handle shorthand: 1.2M, 500K
    multiplier = 1
    if raw.endswith("M"):
        multiplier = 1_000_000
        raw = raw[:-1]
    elif raw.endswith("K"):
        multiplier = 1_000
        raw = raw[:-1]

    try:
        numeric = float(raw) * multiplier
        # Return as integer string if whole number, otherwise float
        if numeric == int(numeric):
            return (str(int(numeric)), True)
        return (f"{numeric:.2f}", True)
    except (ValueError, OverflowError):
        return (value.strip(), False)


def find_matching_columns(headers: List[str], target_set: set[str]) -> List[str]:
    """Find which CSV headers match a target set of column names."""
    return [h for h in headers if h.lower().replace(" ", "_").replace("-", "_") in target_set]


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------
def clean_data(
    input_path: Path,
    output_path: Path,
    fix_addresses: bool = False,
    fix_prices: bool = False,
    fill_missing: bool = False,
) -> Dict[str, int]:
    """
    Read a real estate CSV, apply cleaning operations, and write the result.

    Args:
        input_path: Source CSV path.
        output_path: Destination CSV path.
        fix_addresses: Standardize address abbreviations and casing.
        fix_prices: Strip symbols and convert price strings to numeric.
        fill_missing: Flag rows with missing critical fields.

    Returns:
        Dict with cleaning statistics.
    """
    stats = {
        "total_rows": 0,
        "addresses_cleaned": 0,
        "prices_cleaned": 0,
        "invalid_prices": 0,
        "zips_fixed": 0,
        "invalid_zips": 0,
        "missing_critical_flagged": 0,
    }

    # Read all rows
    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames or [])
        rows: List[Dict[str, str]] = list(reader)

    stats["total_rows"] = len(rows)
    print(f"Read {stats['total_rows']} rows from {input_path.name}")
    print(f"Columns: {', '.join(headers)}")

    # Identify column types
    addr_cols = find_matching_columns(headers, ADDRESS_COLUMNS)
    price_cols = find_matching_columns(headers, PRICE_COLUMNS)
    zip_cols = find_matching_columns(headers, ZIP_COLUMNS)

    # --- Fix addresses ---
    if fix_addresses:
        print(f"\nCleaning addresses in columns: {addr_cols or '(none found)'}")
        for row in rows:
            for col in addr_cols:
                original = row.get(col, "")
                cleaned = clean_address(original)
                if cleaned != original:
                    row[col] = cleaned
                    stats["addresses_cleaned"] += 1

            # Also validate/fix zip codes
            for col in zip_cols:
                raw_zip = row.get(col, "")
                cleaned_zip, is_valid = validate_zip(raw_zip)
                if cleaned_zip != raw_zip:
                    row[col] = cleaned_zip
                    stats["zips_fixed"] += 1
                if raw_zip.strip() and not is_valid:
                    stats["invalid_zips"] += 1

    # --- Fix prices ---
    if fix_prices:
        print(f"\nCleaning prices in columns: {price_cols or '(none found)'}")
        for row in rows:
            for col in price_cols:
                raw_price = row.get(col, "")
                cleaned_price, is_valid = clean_price(raw_price)
                if cleaned_price != raw_price:
                    row[col] = cleaned_price
                    stats["prices_cleaned"] += 1
                if raw_price.strip() and not is_valid:
                    stats["invalid_prices"] += 1

    # --- Flag missing critical fields ---
    if fill_missing:
        print("\nFlagging rows with missing critical fields...")
        critical_present = [h for h in headers if h.lower().replace(" ", "_") in CRITICAL_FIELDS]
        for row in rows:
            missing = [col for col in critical_present if not row.get(col, "").strip()]
            if missing:
                stats["missing_critical_flagged"] += 1
                row["_missing_fields"] = "; ".join(missing)

    # --- Write output ---
    output_headers = list(headers)
    has_missing_col = any("_missing_fields" in row for row in rows)
    if has_missing_col and "_missing_fields" not in output_headers:
        output_headers.append("_missing_fields")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    # --- Summary report ---
    print("\n" + "=" * 60)
    print("DATA CLEANING SUMMARY")
    print("=" * 60)
    print(f"  Total rows processed      : {stats['total_rows']}")
    print(f"  Addresses cleaned         : {stats['addresses_cleaned']}")
    print(f"  Zip codes fixed           : {stats['zips_fixed']}")
    print(f"  Invalid zip codes         : {stats['invalid_zips']}")
    print(f"  Prices cleaned            : {stats['prices_cleaned']}")
    print(f"  Invalid prices            : {stats['invalid_prices']}")
    print(f"  Missing-critical flagged  : {stats['missing_critical_flagged']}")
    print("=" * 60)
    print(f"\nCleaned file written to: {output_path}")

    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="General-purpose data cleaning for real estate CSVs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 clean_data.py listings.csv --fix-addresses --fix-prices\n"
            "  python3 clean_data.py listings.csv --fill-missing --output cleaned.csv\n"
            "  python3 clean_data.py listings.csv --fix-addresses --fix-prices --fill-missing\n"
        ),
    )
    parser.add_argument("input_csv", help="Path to the input CSV file")
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output CSV path (default: <input>_cleaned.csv)",
    )
    parser.add_argument(
        "--fix-addresses",
        action="store_true",
        help="Standardize address abbreviations, casing, and zip codes",
    )
    parser.add_argument(
        "--fix-prices",
        action="store_true",
        help="Strip currency symbols and convert prices to numeric values",
    )
    parser.add_argument(
        "--fill-missing",
        action="store_true",
        help="Flag rows with missing critical fields (address, price, status)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    input_path = Path(args.input_csv)
    if not input_path.exists():
        print(f"Error: file '{input_path}' does not exist.")
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_stem(input_path.stem + "_cleaned")

    clean_data(
        input_path=input_path,
        output_path=output_path,
        fix_addresses=args.fix_addresses,
        fix_prices=args.fix_prices,
        fill_missing=args.fill_missing,
    )
