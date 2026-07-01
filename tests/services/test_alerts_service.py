from packages.services.alerts import evaluate_alert_rules


def test_price_above_triggers_when_close_exceeds_threshold():
    result = evaluate_alert_rules({"price_above": 400}, price=420.5, rsi=None)

    assert result["triggered"] is True
    assert result["rules"][0]["key"] == "price_above"
    assert result["rules"][0]["triggered"] is True


def test_price_above_does_not_trigger_when_close_below_threshold():
    result = evaluate_alert_rules({"price_above": 400}, price=380.0, rsi=None)

    assert result["triggered"] is False
    assert result["rules"][0]["triggered"] is False


def test_rsi_below_triggers_when_rsi_under_threshold():
    result = evaluate_alert_rules({"rsi_below": 30}, price=100.0, rsi=25.0)

    assert result["triggered"] is True
    assert result["rules"][0]["key"] == "rsi_below"
    assert result["rules"][0]["triggered"] is True


def test_combined_rules_trigger_when_any_condition_met():
    result = evaluate_alert_rules(
        {"price_above": 400, "rsi_below": 30},
        price=420.5,
        rsi=35.0,
    )

    assert result["triggered"] is True
    assert len(result["rules"]) == 2
    assert result["rules"][0]["triggered"] is True
    assert result["rules"][1]["triggered"] is False


def test_missing_price_or_rsi_does_not_trigger():
    result = evaluate_alert_rules({"price_above": 400, "rsi_below": 30}, price=None, rsi=None)

    assert result["triggered"] is False
    assert all(rule["triggered"] is False for rule in result["rules"])
