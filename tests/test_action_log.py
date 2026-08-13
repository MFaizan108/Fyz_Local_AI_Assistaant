from memory.action_log import log_action, recent_actions


def test_log_and_recent_actions():
    log_action("test_intent", "test_target", "safe", "did the thing", True)
    entries = recent_actions(limit=1)
    assert entries[0].intent == "test_intent"
    assert entries[0].target == "test_target"
    assert entries[0].level == "safe"
    assert entries[0].executed is True


def test_log_declined_action_records_executed_false():
    log_action("test_intent_declined", None, "dangerous", "cancelled", False)
    entries = recent_actions(limit=1)
    assert entries[0].intent == "test_intent_declined"
    assert entries[0].executed is False
