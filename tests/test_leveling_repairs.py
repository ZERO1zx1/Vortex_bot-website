from src.cogs.games.leveling import _parse_xp_tiers, xp_for_message


def test_malformed_xp_tiers_fall_back_to_safe_entries():
    tiers = _parse_xp_tiers([
        {"max_words": "10", "xp": "5"},
        {"max_words": "bad", "xp": 20},
        "invalid",
        {"max_words": -1, "xp": 50},
    ])
    assert tiers == [{"max_words": 10, "xp": 5}]


def test_message_xp_accepts_malformed_database_value_without_raising():
    assert xp_for_message("one two", {"xp_tiers": [{"max_words": "bad"}]}) == 5


def test_message_xp_uses_sorted_tie_safe_tiers():
    cfg = {"xp_tiers": [{"max_words": 999, "xp": 20}, {"max_words": 10, "xp": 5}]}
    assert xp_for_message("one", cfg) == 5
