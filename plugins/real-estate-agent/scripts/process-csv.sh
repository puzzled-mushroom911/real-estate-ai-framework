#!/usr/bin/env bash
# ============================================================
# Process CSV Data Files
# ============================================================
# Usage:
#   bash scripts/process-csv.sh contacts my_data/leads/contacts.csv
#   bash scripts/process-csv.sh sales my_data/sales_history/sales.csv
#   bash scripts/process-csv.sh reviews my_data/reviews/google_reviews.csv
#
# Cleans, standardizes, and optionally imports CSV data.

set -e

FRAMEWORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="$FRAMEWORK_DIR/tools"

TYPE="${1:?Usage: bash scripts/process-csv.sh <contacts|sales|reviews> file.csv}"
CSV_FILE="${2:?Provide a CSV file path}"

if [ ! -f "$CSV_FILE" ]; then
  echo "ERROR: File not found: $CSV_FILE"
  exit 1
fi

echo "============================================================"
echo "  Processing CSV: $(basename "$CSV_FILE")"
echo "  Type: $TYPE"
echo "============================================================"
echo ""

case "$TYPE" in
  contacts)
    echo "Cleaning and standardizing contacts..."
    python3 "$TOOLS_DIR/csv_tools/clean_data.py" "$CSV_FILE" --type contacts
    echo ""
    echo "Cleaned file saved. You can now:"
    echo "  1. Import to CRM: tell Claude 'import this contact list to my CRM'"
    echo "  2. Index for search: tell Claude 'add this to my knowledge base'"
    ;;

  sales)
    echo "Processing sales history..."
    python3 "$TOOLS_DIR/csv_tools/clean_data.py" "$CSV_FILE" --type sales
    echo ""
    echo "Sales data processed. Claude can now reference your transaction history"
    echo "when generating content or answering market questions."
    ;;

  reviews)
    echo "Processing reviews..."
    python3 "$TOOLS_DIR/csv_tools/clean_data.py" "$CSV_FILE" --type reviews
    echo ""
    echo "Reviews processed. Claude can now reference what clients say about you"
    echo "when writing content or responding to leads."
    ;;

  *)
    echo "Unknown type: $TYPE"
    echo "Supported types: contacts, sales, reviews"
    exit 1
    ;;
esac

echo ""
echo "Done!"
