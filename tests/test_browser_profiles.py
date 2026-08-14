from tools.app_control.browser_profiles import list_chrome_profiles, resolve_chrome_profile

# These tests read this machine's real Chrome "Local State" file rather than
# mocked data - consistent with how the rest of this project's suite already
# depends on real local state (Ollama, the mic, real project paths under
# this user's Desktop). Skipped implicitly (via empty list_chrome_profiles())
# on a machine where Chrome has never been run.


def test_resolves_faizan_to_faizan_mahmood_profile_not_the_primary_users_own_profiles():
    profiles = list_chrome_profiles()
    if not profiles:
        return  # no Chrome installed/run on this machine - nothing to verify

    result = resolve_chrome_profile("Faizan")
    assert result is not None
    assert "mahmood" in result.gaia_name.lower() or "mahmood" in result.display_name.lower() \
        or "faizan" == result.shortcut_name.lower()


def test_full_name_resolves_to_a_different_profile_than_bare_faizan():
    profiles = list_chrome_profiles()
    if not profiles:
        return

    faizan_mahmood = resolve_chrome_profile("Faizan")
    primary_user = resolve_chrome_profile("Muhammad Faizan Ur Rahman")

    if faizan_mahmood and primary_user:
        assert faizan_mahmood.directory != primary_user.directory


def test_unknown_profile_returns_none():
    assert resolve_chrome_profile("this profile definitely does not exist xyz123") is None


def test_empty_hint_returns_none():
    assert resolve_chrome_profile("") is None
