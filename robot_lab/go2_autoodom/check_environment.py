"""Verify the fixed Go2 reproduction environment without changing it."""

from __future__ import annotations

import sys
from importlib import metadata

from .constants import DEFAULT_UNITREE_SDK_DIR


EXPECTED = {
    "isaacsim": "4.5.0.0",
    "isaaclab": "2.1.0",
    "rsl-rl-lib": "2.3.1",
}


def main() -> None:
    errors = []
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    print(f"python={sys.version.split()[0]}")
    if python_version != "3.10":
        errors.append(f"Python 3.10 is required, found {python_version}")
    for distribution, expected in EXPECTED.items():
        try:
            installed = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            installed = "not installed"
        print(f"{distribution}={installed}")
        if installed != expected:
            errors.append(f"{distribution} must be {expected}, found {installed}")
    sdk_present = (DEFAULT_UNITREE_SDK_DIR / "unitree_sdk2py").is_dir()
    print(f"unitree_sdk2_python={DEFAULT_UNITREE_SDK_DIR} present={sdk_present}")
    if errors:
        raise SystemExit("Environment mismatch (no changes were made):\n- " + "\n- ".join(errors))
    print("Fixed prio-tracking software contract is satisfied; no environment changes were made.")


if __name__ == "__main__":
    main()
