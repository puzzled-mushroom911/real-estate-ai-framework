#!/usr/bin/env python3
"""
Secure configuration manager for CRM API credentials.

Stores credentials at ~/.real_estate_ai/crm_config.json with restricted
file permissions (600). Supports environment variable overrides.

Usage:
    python3 crm_config.py [--setup] [--validate] [--show]

Examples:
    python3 crm_config.py --setup        # Interactive configuration
    python3 crm_config.py --validate     # Check credentials are valid
    python3 crm_config.py --show         # Display current config (masked)
"""

import argparse
import json
import os
import stat
import sys
from getpass import getpass
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CONFIG_DIR = Path.home() / ".real_estate_ai"
CONFIG_PATH = CONFIG_DIR / "crm_config.json"
CONFIG_PERMISSIONS = 0o600  # Owner read/write only

# Environment variable names for overrides
ENV_VARS: Dict[str, str] = {
    "api_key": "CRM_API_KEY",
    "location_id": "CRM_LOCATION_ID",
    "endpoint": "CRM_ENDPOINT",
}

# Default configuration values
DEFAULTS: Dict[str, Any] = {
    "api_key": "",
    "location_id": "",
    "endpoint": "https://services.leadconnectorhq.com",
    "timeout": 30,
    "default_limit": 20,
}

# Fields required for the config to be considered valid
REQUIRED_FIELDS = {"api_key", "location_id", "endpoint"}


# ---------------------------------------------------------------------------
# Singleton configuration class
# ---------------------------------------------------------------------------
class CRMConfig:
    """
    Singleton configuration manager for CRM API access.

    Resolution order for each setting:
        1. Environment variable (highest priority)
        2. Config file (~/.real_estate_ai/crm_config.json)
        3. Default value
    """

    _instance: Optional["CRMConfig"] = None
    _config: Dict[str, Any]

    def __new__(cls) -> "CRMConfig":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = {}
            cls._instance._load()
        return cls._instance

    # --- Loading and saving ---

    def _load(self) -> None:
        """Load config from file, then apply environment variable overrides."""
        # Start with defaults
        self._config = dict(DEFAULTS)

        # Layer in file config
        if CONFIG_PATH.exists():
            try:
                file_config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                self._config.update(file_config)
            except (json.JSONDecodeError, OSError) as exc:
                print(f"Warning: could not read config file: {exc}", file=sys.stderr)

        # Layer in environment variables (highest priority)
        for config_key, env_var in ENV_VARS.items():
            env_value = os.environ.get(env_var)
            if env_value:
                self._config[config_key] = env_value

    def _save(self) -> None:
        """Write config to disk with restricted permissions."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Write the file
        CONFIG_PATH.write_text(
            json.dumps(self._config, indent=2),
            encoding="utf-8",
        )

        # Set restrictive permissions (owner read/write only)
        CONFIG_PATH.chmod(CONFIG_PERMISSIONS)

    def reload(self) -> None:
        """Force reload from disk and environment."""
        self._load()

    # --- Getters and setters ---

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and persist to disk."""
        self._config[key] = value
        self._save()

    @property
    def api_key(self) -> str:
        return str(self._config.get("api_key", ""))

    @property
    def location_id(self) -> str:
        return str(self._config.get("location_id", ""))

    @property
    def endpoint(self) -> str:
        return str(self._config.get("endpoint", DEFAULTS["endpoint"]))

    @property
    def timeout(self) -> int:
        return int(self._config.get("timeout", DEFAULTS["timeout"]))

    @property
    def default_limit(self) -> int:
        return int(self._config.get("default_limit", DEFAULTS["default_limit"]))

    # --- Validation ---

    def validate(self) -> Dict[str, bool]:
        """
        Check whether all required fields are populated.

        Returns:
            Dict mapping each required field to True (present) or False (missing).
        """
        results: Dict[str, bool] = {}
        for field in REQUIRED_FIELDS:
            value = self._config.get(field, "")
            results[field] = bool(value and str(value).strip())
        return results

    def is_valid(self) -> bool:
        """Return True if all required fields are populated."""
        return all(self.validate().values())

    # --- Display ---

    def to_display_dict(self) -> Dict[str, str]:
        """Return config with sensitive values masked for display."""
        display = {}
        for key, value in self._config.items():
            str_value = str(value)
            if key == "api_key" and str_value:
                # Show first 8 and last 4 chars only
                if len(str_value) > 12:
                    display[key] = f"{str_value[:8]}...{str_value[-4:]}"
                else:
                    display[key] = "****"
            else:
                display[key] = str_value
        return display


# ---------------------------------------------------------------------------
# Interactive setup
# ---------------------------------------------------------------------------
def interactive_setup() -> None:
    """Run an interactive prompt to configure CRM credentials."""
    config = CRMConfig()

    print("=" * 60)
    print("CRM Configuration Setup")
    print("=" * 60)
    print("Enter your CRM API credentials below.")
    print("Press Enter to keep existing values (shown in brackets).\n")

    # API key (hidden input)
    current_key = config.api_key
    key_display = f"{current_key[:8]}...{current_key[-4:]}" if len(current_key) > 12 else "(not set)"
    new_key = getpass(f"API Key [{key_display}]: ").strip()
    if new_key:
        config.set("api_key", new_key)

    # Location ID
    current_loc = config.location_id
    loc_display = current_loc or "(not set)"
    new_loc = input(f"Location ID [{loc_display}]: ").strip()
    if new_loc:
        config.set("location_id", new_loc)

    # Endpoint
    current_endpoint = config.endpoint
    new_endpoint = input(f"API Endpoint [{current_endpoint}]: ").strip()
    if new_endpoint:
        config.set("endpoint", new_endpoint)

    # Timeout
    current_timeout = config.timeout
    new_timeout = input(f"Request timeout in seconds [{current_timeout}]: ").strip()
    if new_timeout:
        try:
            config.set("timeout", int(new_timeout))
        except ValueError:
            print(f"  Invalid timeout value, keeping {current_timeout}")

    # Default limit
    current_limit = config.default_limit
    new_limit = input(f"Default query limit [{current_limit}]: ").strip()
    if new_limit:
        try:
            config.set("default_limit", int(new_limit))
        except ValueError:
            print(f"  Invalid limit value, keeping {current_limit}")

    print(f"\nConfiguration saved to {CONFIG_PATH}")
    print(f"File permissions: {oct(CONFIG_PERMISSIONS)}")

    # Validate
    validation = config.validate()
    all_valid = all(validation.values())
    print(f"\nValidation: {'PASSED' if all_valid else 'INCOMPLETE'}")
    for field, valid in validation.items():
        status = "OK" if valid else "MISSING"
        print(f"  {field}: {status}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage CRM API configuration securely.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Environment variable overrides:\n"
            "  CRM_API_KEY      - API key\n"
            "  CRM_LOCATION_ID  - Location/account ID\n"
            "  CRM_ENDPOINT     - API base URL\n\n"
            "Examples:\n"
            "  python3 crm_config.py --setup\n"
            "  python3 crm_config.py --validate\n"
            "  python3 crm_config.py --show\n"
        ),
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run interactive configuration setup",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate that all required fields are configured",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display current configuration (API key masked)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if not any([args.setup, args.validate, args.show]):
        print("No action specified. Use --setup, --validate, or --show.")
        print("Run with --help for more information.")
        sys.exit(1)

    if args.setup:
        interactive_setup()

    if args.validate:
        config = CRMConfig()
        validation = config.validate()
        all_valid = all(validation.values())
        print(f"Configuration: {'VALID' if all_valid else 'INCOMPLETE'}")
        for field, valid in validation.items():
            status = "OK" if valid else "MISSING"
            print(f"  {field}: {status}")
        if not all_valid:
            print(f"\nRun 'python3 crm_config.py --setup' to configure.")
            sys.exit(1)

    if args.show:
        config = CRMConfig()
        print("=" * 60)
        print("Current CRM Configuration")
        print("=" * 60)
        print(f"  Config file: {CONFIG_PATH}")
        exists = CONFIG_PATH.exists()
        print(f"  File exists: {exists}")
        if exists:
            perms = oct(stat.S_IMODE(CONFIG_PATH.stat().st_mode))
            print(f"  Permissions: {perms}")
        print()
        for key, value in config.to_display_dict().items():
            print(f"  {key}: {value}")
        print("=" * 60)
