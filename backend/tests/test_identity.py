from app.services.identity import resolve_identity


def test_strong_identifier_confirms_identity():
    decision = resolve_identity({"mac": "aa"}, {"mac": "aa"})
    assert decision.outcome == "confirmed_match"


def test_ip_only_never_confirms_identity():
    decision = resolve_identity({"ip": "192.0.2.1"}, {"ip": "192.0.2.1"})
    assert decision.outcome != "confirmed_match"


def test_conflicting_strong_identifiers_block_merge():
    decision = resolve_identity({"mac": "aa", "serial": "one"}, {"mac": "aa", "serial": "two"})
    assert decision.outcome == "potentially_separate"
