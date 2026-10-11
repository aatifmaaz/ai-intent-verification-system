import pytest
from app.services.intent_parser import IntentParser

def test_deny_intent_parsing():
    parser = IntentParser()
    res = parser.parse("The HR network must not communicate with the guest network.")
    assert res["status"] == "parsed"
    assert res["confidence"] >= 0.8
    assert len(res["policies"]) == 1
    p = res["policies"][0]
    assert p["policy_type"] == "deny"
    assert p["action"] == "deny"
    assert "hr" in p["source_zone"].lower()
    assert "guest" in p["destination_zone"].lower()

def test_allow_intent_parsing():
    parser = IntentParser()
    res = parser.parse("All devices in the engineering network must be able to access the internal application server.")
    assert res["status"] == "parsed"
    assert len(res["policies"]) == 1
    p = res["policies"][0]
    assert p["policy_type"] == "allow"
    assert p["action"] == "permit"

def test_isolate_intent_parsing():
    parser = IntentParser()
    res = parser.parse("The backup network must remain isolated from ordinary user traffic.")
    assert res["status"] == "parsed"
    p = res["policies"][0]
    assert p["policy_type"] == "isolate"
    assert p["action"] == "deny"

def test_compound_intent_parsing():
    parser = IntentParser()
    res = parser.parse("Guest devices must have internet access but must not access internal servers.")
    assert res["status"] == "parsed"
    assert len(res["policies"]) == 2
    assert any(p["action"] == "permit" for p in res["policies"])
    assert any(p["action"] == "deny" for p in res["policies"])

def test_unrecognized_intent():
    parser = IntentParser()
    res = parser.parse("Random unstructured sentence with no networking keywords.")
    assert res["status"] == "draft"
    assert res["confidence"] == 0.0
    assert len(res["policies"]) == 0
