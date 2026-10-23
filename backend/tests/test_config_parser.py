import pytest
from app.services.config_parser import ConfigParser

def test_parse_json_configuration():
    parser = ConfigParser()
    raw_json = '''
    {
        "hostname": "core-router-01",
        "interfaces": [{"name": "GigabitEthernet0/0", "ip_address": "10.0.0.1", "subnet_mask": "255.255.255.0"}],
        "acls": [{"name": "standard-acl", "rules": [{"action": "permit", "protocol": "ip", "source": "any", "destination": "any"}]}],
        "routes": [{"network": "10.1.0.0", "mask": "255.255.0.0", "next_hop": "10.0.0.254"}]
    }
    '''
    result = parser.parse(raw_json, "json")
    assert result["hostname"] == "core-router-01"
    assert len(result["interfaces"]) == 1
    assert len(result["acls"]) == 1
    assert len(result["routes"]) == 1

def test_parse_yaml_configuration():
    parser = ConfigParser()
    raw_yaml = '''
    hostname: edge-firewall
    interfaces:
      - name: eth0
        ip_address: 192.168.1.1
    acls:
      - name: outside-in
        rules:
          - action: deny
            protocol: tcp
            source: any
            destination: any
            port: 23
    '''
    result = parser.parse(raw_yaml, "yaml")
    assert result["hostname"] == "edge-firewall"
    assert len(result["acls"]) == 1
    assert result["acls"][0]["rules"][0]["action"] == "deny"

def test_parse_cisco_ios_configuration():
    parser = ConfigParser()
    raw_ios = '''
    hostname cisco-switch-1
    !
    interface GigabitEthernet0/1
     ip address 10.10.10.1 255.255.255.0
     no shutdown
    !
    ip route 10.20.0.0 255.255.0.0 10.10.10.254
    !
    access-list 101 permit tcp any any eq 443
    access-list 101 deny ip any any
    '''
    result = parser.parse(raw_ios, "ios")
    assert "hostname" in result or "interfaces" in result
    assert isinstance(result, dict)

def test_unsupported_format_raises_error():
    parser = ConfigParser()
    with pytest.raises(ValueError, match="Unsupported format"):
        parser.parse("some content", "unknown_format")

def test_empty_configuration_raises_error():
    parser = ConfigParser()
    with pytest.raises(ValueError, match="cannot be empty"):
        parser.parse("", "json")
    with pytest.raises(ValueError, match="cannot be empty"):
        parser.parse("   ", "yaml")

def test_malformed_json_raises_error():
    parser = ConfigParser()
    with pytest.raises(ValueError, match="Invalid JSON"):
        parser.parse("{hostname: missing_quotes}", "json")

def test_json_non_dict_raises_error():
    parser = ConfigParser()
    with pytest.raises(ValueError, match="top-level must be an object"):
        parser.parse('["item1", "item2"]', "json")

def test_malformed_yaml_raises_error():
    parser = ConfigParser()
    with pytest.raises(ValueError, match="Invalid YAML"):
        parser.parse("hostname: [unclosed list", "yaml")

def test_yaml_non_dict_raises_error():
    parser = ConfigParser()
    with pytest.raises(ValueError, match="top-level must be a key-value mapping"):
        parser.parse("- item1\n- item2", "yaml")

def test_invalid_ip_in_acl_raises_error():
    parser = ConfigParser()
    bad_json = '''
    {
        "hostname": "router-1",
        "acls": [{"name": "bad-acl", "rules": [{"action": "permit", "protocol": "ip", "source": "999.999.999.999", "destination": "any"}]}]
    }
    '''
    with pytest.raises(ValueError, match="Invalid source IP/CIDR"):
        parser.parse(bad_json, "json")

def test_invalid_port_range_raises_error():
    parser = ConfigParser()
    bad_json = '''
    {
        "hostname": "router-1",
        "acls": [{"name": "bad-acl", "rules": [{"action": "permit", "protocol": "tcp", "source": "any", "destination": "any", "port": 99999}]}]
    }
    '''
    with pytest.raises(ValueError, match="Invalid port number"):
        parser.parse(bad_json, "json")

def test_ios_unsupported_commands_captured():
    parser = ConfigParser()
    ios_cfg = '''
    hostname test-switch
    !
    spanning-tree mode rapid-pvst
    spanning-tree portfast default
    !
    interface GigabitEthernet0/1
     ip address 10.0.0.1 255.255.255.0
    '''
    result = parser.parse(ios_cfg, "ios")
    assert result["hostname"] == "test-switch"
    assert len(result["unsupported_commands"]) >= 2
    cmd_texts = [cmd["command"] for cmd in result["unsupported_commands"]]
    assert any("spanning-tree" in c for c in cmd_texts)

def test_validate_method():
    parser = ConfigParser()
    errors = parser.validate("")
    assert len(errors) > 0
    assert "Empty" in errors[0]["error"]

    valid_errors = parser.validate('{"hostname": "router-ok"}', "json")
    assert len(valid_errors) == 0

