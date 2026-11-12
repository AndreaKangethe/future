from app.connectors.scan_import import (
    import_scan,
    parse_csv,
    parse_json,
    parse_nessus_csv,
    parse_nmap_xml,
)


def test_nmap_xml_emits_normalized_host_and_services():
    observations = parse_nmap_xml(
        """<nmaprun><host><status state="up"/>
        <address addr="192.0.2.10" addrtype="ipv4"/>
        <address addr="AABBCCDDEEFF" addrtype="mac"/>
        <hostnames><hostname name="WEB-01.EXAMPLE.COM."/></hostnames>
        <ports><port protocol="tcp" portid="443"><state state="open"/>
        <service name="https" product="nginx" version="1"/></port></ports>
        </host></nmaprun>"""
    )
    assert len(observations) == 1
    observation = observations[0]
    assert observation["asset_identifiers"] == {
        "ip": "192.0.2.10",
        "mac": "aa:bb:cc:dd:ee:ff",
        "hostname": "web-01.example.com",
    }
    assert observation["observed_attributes"]["ports"][0]["port"] == "443"


def test_generic_csv_separates_identifiers_and_attributes():
    observations = parse_csv("Hostname,IP,owner\napp.EXAMPLE.com,2001:db8::1,platform\n")
    assert observations[0]["asset_identifiers"] == {
        "hostname": "app.example.com",
        "ip": "2001:db8::1",
    }
    assert observations[0]["observed_attributes"] == {"owner": "platform"}


def test_json_array_and_nessus_finding_import():
    json_observations = parse_json('[{"hostname": "db-1", "port": 5432}]')
    assert json_observations[0]["asset_identifiers"] == {"hostname": "db-1"}
    assert json_observations[0]["observed_attributes"]["port"] == 5432

    nessus = parse_nessus_csv(
        "Host,Port,Severity,Plugin Name,Scan Date\n"
        "DB-1.example.com,443,High,TLS issue,2026-01-02T03:04:05Z\n"
    )
    assert nessus[0]["source_type"] == "nessus"
    assert nessus[0]["observation_category"] == "finding"
    assert nessus[0]["asset_identifiers"] == {"host": "db-1.example.com"}
    assert nessus[0]["observed_attributes"]["scanner"] == "nessus"


def test_import_scan_dispatches_by_filename():
    observations = import_scan("hostname,owner\nhost-1,security\n", filename="assets.csv")
    assert observations[0]["source_name"] == "csv"
