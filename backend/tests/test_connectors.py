from types import SimpleNamespace

from app.connectors.aws import AWSConnector
from app.connectors.demo import DemoConnector
from app.connectors.docker import DockerConnector
from app.connectors.kubernetes import KubernetesConnector
from app.connectors.scan_import import (
    import_scan,
    parse_csv,
    parse_json,
    parse_nessus_csv,
    parse_nmap_xml,
)


def test_demo_connector_is_deterministic_and_declares_capabilities():
    observations = list(DemoConnector().collect())
    assert len(observations) == 2
    assert "read" in DemoConnector.capabilities
    assert observations[0]["source_type"] == "demo"


def test_docker_connector_uses_only_read_operations():
    container = SimpleNamespace(
        id="abc",
        name="web",
        status="running",
        attrs={
            "Config": {"Image": "nginx", "Labels": {"tier": "web"}},
            "State": {"Status": "running"},
            "NetworkSettings": {"Ports": {}},
        },
    )
    image = SimpleNamespace(id="sha256:image", tags=["nginx:latest"], attrs={"Size": 10})

    class Client:
        containers = SimpleNamespace(list=lambda all=False: [container])
        images = SimpleNamespace(list=lambda: [image])

        def version(self):
            return {"Version": "test"}

    observations = list(DockerConnector(client=Client()).collect())
    assert [item["observed_attributes"]["kind"] for item in observations] == ["container", "image"]


def test_kubernetes_connector_collects_resources_from_mocked_clients():
    metadata = SimpleNamespace(name="web", namespace="default", uid="uid-1", labels={"app": "web"})
    resource = SimpleNamespace(metadata=metadata)

    class Core:
        def list_node(self):
            return SimpleNamespace(items=[resource])

        def list_pod_for_all_namespaces(self):
            return SimpleNamespace(items=[resource])

        def list_service_for_all_namespaces(self):
            return SimpleNamespace(items=[resource])

        def list_namespace(self):
            return SimpleNamespace(items=[resource])

    class Apps:
        def list_deployment_for_all_namespaces(self):
            return SimpleNamespace(items=[resource])

    client = SimpleNamespace(CoreV1Api=lambda: Core(), AppsV1Api=lambda: Apps())
    observations = list(KubernetesConnector(client=client).collect())
    assert len(observations) == 5
    assert {item["observed_attributes"]["kind"] for item in observations} == {
        "node",
        "pod",
        "service",
        "namespace",
        "deployment",
    }


def test_aws_connector_collects_metadata_with_mocked_session():
    class Paginator:
        def paginate(self):
            return [{"Reservations": [{"Instances": [{"InstanceId": "i-1"}]}]}]

    class Client:
        def __init__(self, service):
            self.service = service

        def get_paginator(self, _):
            return Paginator()

        def describe_vpcs(self):
            return {"Vpcs": [{"VpcId": "vpc-1"}]}

        def describe_security_groups(self):
            return {"SecurityGroups": [{"GroupId": "sg-1"}]}

        def describe_db_instances(self):
            return {"DBInstances": [{"DBInstanceIdentifier": "db-1"}]}

        def list_buckets(self):
            return {"Buckets": [{"Name": "bucket-1"}]}

        def describe_load_balancers(self):
            return {"LoadBalancers": [{"LoadBalancerArn": "arn:lb"}]}

    class Session:
        def client(self, service):
            return Client(service)

    observations = list(AWSConnector(session=Session()).collect())
    assert len(observations) == 6
    assert {item["observed_attributes"]["kind"] for item in observations} == {
        "ec2_instance",
        "vpc",
        "security_group",
        "rds_instance",
        "s3_bucket",
        "load_balancer",
    }


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
