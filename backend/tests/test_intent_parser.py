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

def test_everyday_english_access_requirements():
    parser = IntentParser()
    cases = [
        ("Engineering should have access to the application server", "engineering", "application"),
        ("The application server must be reachable by engineering", "engineering", "application"),
        ("Engineering is permitted to connect to the application server", "engineering", "application"),
    ]
    for sentence, expected_source, expected_destination in cases:
        result = parser.parse(sentence)
        policy = result["policies"][0]
        assert policy["action"] == "permit", sentence
        assert policy["source_zone"] == expected_source, sentence
        assert policy["destination_zone"] == expected_destination, sentence

def test_everyday_english_denials_and_restricted_access():
    parser = IntentParser()
    for sentence, expected_destination in (
        ("Guests cannot communicate with the database", "database"),
        ("Keep guest users out of HR", "hr"),
        ("Guest users must not be able to connect to HR", "hr"),
    ):
        policy = parser.parse(sentence)["policies"][0]
        assert policy["action"] == "deny", sentence
        assert policy["source_zone"] == "guest", sentence
        assert policy["destination_zone"] == expected_destination, sentence

    result = parser.parse("Database access must remain restricted to the application server")
    policy = result["policies"][0]
    assert policy["policy_type"] == "require"
    assert policy["action"] == "permit"
    assert policy["source_zone"] == "application"
    assert policy["destination_zone"] == "database"

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

def test_cidr_explicit_intent_parsing():
    parser = IntentParser()
    res = parser.parse("Block all connections from 10.1.30.0/24 to 10.1.60.0/24")
    assert res["status"] == "parsed"
    p = res["policies"][0]
    assert p["action"] == "deny"
    assert p["source_network"] == "10.1.30.0/24"
    assert p["destination_network"] == "10.1.60.0/24"

def test_short_device_to_device_deny_command_uses_host_routes(db_session):
    parser = IntentParser()
    result = parser.parse("stop edge-router from core-router", db=db_session)

    assert result["status"] == "parsed"
    policy = result["policies"][0]
    assert policy["action"] == "deny"
    assert policy["source_zone"] == "edge"
    assert policy["destination_zone"] == "core"
    assert policy["source_network"] == "10.0.1.1/32"
    assert policy["destination_network"] == "10.0.0.1/32"

def test_inverted_asset_protection_parsing():
    parser = IntentParser()
    # "Keep the database private from guests" -> guest is untrusted source, database is protected destination
    res = parser.parse("Keep the database private from guests")
    assert res["status"] == "parsed"
    p = res["policies"][0]
    assert p["action"] == "deny"
    assert p["source_zone"] == "guest"
    assert p["destination_zone"] == "database"

def test_multi_topology_templates_parsing():
    parser = IntentParser()
    # Healthcare
    h_res = parser.parse("Visitor patient wifi must not communicate with the EHR database.")
    assert h_res["status"] == "parsed"
    hp = h_res["policies"][0]
    assert hp["action"] == "deny"
    assert hp["source_zone"] == "guest"
    assert hp["destination_zone"] == "database"

    # FinTech
    f_res = parser.parse("Payment API gateway must not communicate directly with the cardholder vault database.")
    assert f_res["status"] == "parsed"
    fp = f_res["policies"][0]
    assert fp["action"] == "deny"
    assert fp["source_zone"] == "dmz"
    assert fp["destination_zone"] == "database"

    # Datacenter Spine-Leaf
    d_res = parser.parse("Only the bastion host may access the k8s control plane using SSH.")
    assert d_res["status"] == "parsed"
    dp = d_res["policies"][0]
    assert dp["source_zone"] == "management"
    assert dp["destination_zone"] == "compute"
    assert dp["port"] == "22"

def test_unrecognized_with_and_without_fallback():
    parser = IntentParser()
    res = parser.parse("Random unstructured sentence with no networking keywords.", fallback_on_unrecognized=False)
    assert res["status"] == "draft"
    assert res["confidence"] == 0.0
    assert len(res["policies"]) == 0

    fallback_res = parser.parse("Ensure bad guys cannot enter our network", fallback_on_unrecognized=True)
    assert fallback_res["status"] == "parsed"
    assert len(fallback_res["policies"]) == 1
    assert fallback_res["policies"][0]["action"] == "deny"
