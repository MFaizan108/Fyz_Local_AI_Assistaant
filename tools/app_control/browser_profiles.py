"""Chrome profile resolution - reads the real profiles configured on this
machine from Chrome's own "Local State" file rather than guessing or
hardcoding a profile directory (directory numbering like "Profile 29" isn't
predictable and differs per machine/reinstall)."""

import json
import os
import subprocess
from dataclasses import dataclass
from typing import List, Optional

_LOCAL_STATE_PATH = os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data", "Local State"
)

# Short aliases -> the search term to match against a real profile's own
# name fields below. This does NOT hardcode a profile directory/path - the
# actual directory is always resolved live from list_chrome_profiles(), so
# this stays correct even if Chrome profiles get added, removed, or
# renumbered later.
PROFILE_ALIASES = {
    "faizan": "faizan mahmood",
    "faizan mahmood": "faizan mahmood",
}


@dataclass
class ChromeProfile:
    directory: str  # e.g. "Default", "Profile 29" - what Chrome's --profile-directory flag needs
    display_name: str
    shortcut_name: str
    account_email: str
    gaia_name: str


def list_chrome_profiles() -> List[ChromeProfile]:
    """Enumerates the real Chrome profiles on this machine straight from
    Chrome's own Local State JSON file. Returns an empty list if Chrome
    isn't installed or has never been run (no Local State file yet)."""
    if not os.path.isfile(_LOCAL_STATE_PATH):
        return []

    with open(_LOCAL_STATE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    profiles = []
    for directory, info in data.get("profile", {}).get("info_cache", {}).items():
        profiles.append(
            ChromeProfile(
                directory=directory,
                display_name=info.get("name", ""),
                shortcut_name=info.get("shortcut_name", ""),
                account_email=info.get("user_name", ""),
                gaia_name=info.get("gaia_name", ""),
            )
        )
    return profiles


def resolve_chrome_profile(hint: str) -> Optional[ChromeProfile]:
    """Finds the real Chrome profile matching a free-text hint (e.g.
    "Faizan", "Faizan Mahmood"). Tries strongest signal first so this stays
    deterministic even when multiple profiles share a name fragment (this
    machine has 3 separate profiles containing "Faizan" from the primary
    user's own accounts, plus a distinct "Faizan Mahmood" profile) - an
    exact match on the short/gaia/display name always wins over a loose
    substring match."""
    if not hint:
        return None

    query = PROFILE_ALIASES.get(hint.strip().lower(), hint.strip().lower())
    profiles = list_chrome_profiles()
    if not profiles:
        return None

    for p in profiles:
        if p.shortcut_name.strip().lower() == query:
            return p

    for p in profiles:
        if p.gaia_name.strip().lower() == query or p.display_name.strip().lower() == query:
            return p

    query_words = set(query.split())
    best: Optional[ChromeProfile] = None
    best_score = 0
    for p in profiles:
        haystack = f"{p.display_name} {p.shortcut_name} {p.gaia_name}".lower()
        score = sum(1 for w in query_words if w in haystack)
        if score > best_score:
            best, best_score = p, score

    return best


def open_chrome_profile(hint: str) -> str:
    """Launches Chrome directly into the resolved profile - a single
    process launch, not "open Chrome" followed by a separate profile-switch
    step, so this never opens two Chrome windows for one request."""
    profile = resolve_chrome_profile(hint)
    if profile is None:
        return f"Mujhe '{hint}' naam ka koi Chrome profile nahi mila bhai."

    subprocess.Popen(
        ["cmd", "/c", "start", "", "chrome", f"--profile-directory={profile.directory}"],
        shell=False,
    )
    label = profile.shortcut_name or profile.display_name
    return f"Chrome '{label}' profile ke saath khol raha hoon bhai 😄"
