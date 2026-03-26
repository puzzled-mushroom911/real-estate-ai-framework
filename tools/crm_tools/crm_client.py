#!/usr/bin/env python3
"""
Generic CRM API client for GoHighLevel or similar REST APIs.

Provides methods for contacts, conversations, opportunities, and messaging.
Reads credentials from CRMConfig (file + env vars) or accepts them directly.

Usage:
    # As a library
    from crm_client import CRMClient
    client = CRMClient()
    contacts = client.search_contacts("John Smith")

    # CLI mode for testing
    python3 crm_client.py search "John Smith"
    python3 crm_client.py get-contact <contact_id>
    python3 crm_client.py send-message <contact_id> "Hello!"

Examples:
    python3 crm_client.py search "John Smith"
    python3 crm_client.py get-contact abc123
    python3 crm_client.py search-deals "New lead"
    python3 crm_client.py conversations abc123
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# Import CRMConfig from the same directory
sys.path.insert(0, str(Path(__file__).parent))
from crm_config import CRMConfig

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
DEFAULT_TIMEOUT = 30


# ---------------------------------------------------------------------------
# CRM Client
# ---------------------------------------------------------------------------
class CRMClient:
    """
    Generic CRM API client with retry logic and structured error handling.

    Works with GoHighLevel's API or any REST API that follows similar
    patterns (Bearer auth, JSON payloads, location-scoped queries).
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        location_id: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        """
        Initialize the CRM client.

        Args:
            endpoint: API base URL. Falls back to CRMConfig.
            api_key: API key / Bearer token. Falls back to CRMConfig.
            location_id: Location/account scope ID. Falls back to CRMConfig.
            timeout: Request timeout in seconds. Falls back to CRMConfig.
        """
        config = CRMConfig()

        self.endpoint = (endpoint or config.endpoint).rstrip("/")
        self.api_key = api_key or config.api_key
        self.location_id = location_id or config.location_id
        self.timeout = timeout or config.timeout or DEFAULT_TIMEOUT
        self.default_limit = config.default_limit

        if not self.api_key:
            raise ValueError(
                "No API key configured. Run 'python3 crm_config.py --setup' "
                "or set the CRM_API_KEY environment variable."
            )

    @property
    def _headers(self) -> Dict[str, str]:
        """Standard request headers with authorization."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Version": "2021-07-28",
        }

    # --- HTTP helpers ---

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: API path (appended to endpoint).
            params: Query parameters.
            data: JSON body payload.

        Returns:
            Parsed JSON response.

        Raises:
            requests.HTTPError: On non-retryable HTTP errors.
            ConnectionError: After exhausting retries.
        """
        url = f"{self.endpoint}/{path.lstrip('/')}"

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self._headers,
                    params=params,
                    json=data,
                    timeout=self.timeout,
                )

                # Retry on server errors and rate limits
                if response.status_code in (429, 500, 502, 503, 504):
                    if attempt < MAX_RETRIES:
                        wait = RETRY_DELAY_SECONDS * attempt
                        print(f"  Retry {attempt}/{MAX_RETRIES} after {response.status_code}, waiting {wait}s...")
                        time.sleep(wait)
                        continue

                response.raise_for_status()

                # Some endpoints return empty body on success
                if not response.text:
                    return {"status": "success"}

                return response.json()

            except requests.ConnectionError as exc:
                if attempt < MAX_RETRIES:
                    wait = RETRY_DELAY_SECONDS * attempt
                    print(f"  Connection error, retry {attempt}/{MAX_RETRIES} in {wait}s...")
                    time.sleep(wait)
                else:
                    raise ConnectionError(
                        f"Failed to connect to {url} after {MAX_RETRIES} attempts"
                    ) from exc

            except requests.Timeout as exc:
                if attempt < MAX_RETRIES:
                    wait = RETRY_DELAY_SECONDS * attempt
                    print(f"  Timeout, retry {attempt}/{MAX_RETRIES} in {wait}s...")
                    time.sleep(wait)
                else:
                    raise ConnectionError(
                        f"Request to {url} timed out after {MAX_RETRIES} attempts"
                    ) from exc

        # Should not reach here, but just in case
        raise ConnectionError(f"Failed request to {url}")

    # --- Contact operations ---

    def search_contacts(self, query: str, limit: int = 0) -> List[Dict[str, Any]]:
        """
        Search contacts by name, email, or phone.

        Args:
            query: Search string.
            limit: Max results (0 = use default_limit from config).

        Returns:
            List of contact dicts.
        """
        effective_limit = limit or self.default_limit
        response = self._request("GET", "/contacts/", params={
            "locationId": self.location_id,
            "query": query,
            "limit": effective_limit,
        })
        return response.get("contacts", [])

    def get_contact(self, contact_id: str) -> Dict[str, Any]:
        """
        Retrieve full details for a single contact.

        Args:
            contact_id: The contact's unique ID.

        Returns:
            Contact details dict.
        """
        response = self._request("GET", f"/contacts/{contact_id}")
        return response.get("contact", response)

    def create_contact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new contact.

        Args:
            data: Contact fields (firstName, lastName, email, phone, etc.).

        Returns:
            Created contact dict.
        """
        payload = {**data, "locationId": self.location_id}
        response = self._request("POST", "/contacts/", data=payload)
        return response.get("contact", response)

    def update_contact(self, contact_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing contact.

        Args:
            contact_id: The contact's unique ID.
            data: Fields to update.

        Returns:
            Updated contact dict.
        """
        response = self._request("PUT", f"/contacts/{contact_id}", data=data)
        return response.get("contact", response)

    # --- Messaging ---

    def send_message(
        self,
        contact_id: str,
        message: str,
        message_type: str = "SMS",
    ) -> Dict[str, Any]:
        """
        Send a message to a contact.

        Args:
            contact_id: Recipient contact ID.
            message: Message body text.
            message_type: Message channel -- "SMS", "Email", "WhatsApp", etc.

        Returns:
            Message result dict.
        """
        payload = {
            "type": message_type,
            "contactId": contact_id,
            "message": message,
        }
        return self._request("POST", "/conversations/messages", data=payload)

    # --- Opportunities / Deals ---

    def search_opportunities(self, query: str, limit: int = 0) -> List[Dict[str, Any]]:
        """
        Search opportunities/deals by name or pipeline stage.

        Args:
            query: Search string.
            limit: Max results (0 = use default_limit from config).

        Returns:
            List of opportunity dicts.
        """
        effective_limit = limit or self.default_limit
        response = self._request("GET", "/opportunities/search", params={
            "locationId": self.location_id,
            "q": query,
            "limit": effective_limit,
        })
        return response.get("opportunities", [])

    # --- Conversations ---

    def get_conversations(self, contact_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve conversation history for a contact.

        Args:
            contact_id: The contact's unique ID.

        Returns:
            List of message dicts.
        """
        response = self._request("GET", f"/conversations/search", params={
            "locationId": self.location_id,
            "contactId": contact_id,
        })
        return response.get("conversations", [])


# ---------------------------------------------------------------------------
# CLI display helpers
# ---------------------------------------------------------------------------
def format_contact(contact: Dict[str, Any]) -> str:
    """Format a contact dict for terminal display."""
    name = f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip()
    email = contact.get("email", "")
    phone = contact.get("phone", "")
    cid = contact.get("id", "unknown")
    return f"  [{cid}] {name}  |  {email}  |  {phone}"


def format_opportunity(opp: Dict[str, Any]) -> str:
    """Format an opportunity dict for terminal display."""
    name = opp.get("name", opp.get("contact", {}).get("name", "Unknown"))
    stage = opp.get("pipelineStageId", "")
    value = opp.get("monetaryValue", "")
    oid = opp.get("id", "unknown")
    return f"  [{oid}] {name}  |  Stage: {stage}  |  Value: {value}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CRM API client -- test mode.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Commands:\n"
            '  search "query"          Search contacts\n'
            "  get-contact <id>        Get contact details\n"
            '  search-deals "query"    Search opportunities\n'
            "  conversations <id>      Get conversation history\n\n"
            "Examples:\n"
            '  python3 crm_client.py search "John Smith"\n'
            "  python3 crm_client.py get-contact abc123\n"
            '  python3 crm_client.py search-deals "pipeline"\n'
        ),
    )
    parser.add_argument("command", help="Command to run")
    parser.add_argument("argument", help="Search query or contact ID")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max results for search commands (default: use config)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output raw JSON instead of formatted text",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    try:
        client = CRMClient()
    except ValueError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    command = args.command.lower()

    try:
        if command == "search":
            results = client.search_contacts(args.argument, limit=args.limit)
            if args.json_output:
                print(json.dumps(results, indent=2))
            else:
                print(f"Found {len(results)} contact(s) for '{args.argument}':")
                for c in results:
                    print(format_contact(c))

        elif command == "get-contact":
            contact = client.get_contact(args.argument)
            if args.json_output:
                print(json.dumps(contact, indent=2))
            else:
                print(f"Contact details for {args.argument}:")
                print(format_contact(contact))

        elif command == "search-deals":
            results = client.search_opportunities(args.argument, limit=args.limit)
            if args.json_output:
                print(json.dumps(results, indent=2))
            else:
                print(f"Found {len(results)} opportunity(ies) for '{args.argument}':")
                for o in results:
                    print(format_opportunity(o))

        elif command == "conversations":
            results = client.get_conversations(args.argument)
            if args.json_output:
                print(json.dumps(results, indent=2))
            else:
                print(f"Conversations for contact {args.argument}:")
                for conv in results:
                    print(f"  [{conv.get('id', '')}] {conv.get('type', '')} - {conv.get('lastMessageDate', '')}")

        else:
            print(f"Unknown command: {command}")
            print("Valid commands: search, get-contact, search-deals, conversations")
            sys.exit(1)

    except (requests.HTTPError, ConnectionError) as exc:
        print(f"API Error: {exc}")
        sys.exit(1)
