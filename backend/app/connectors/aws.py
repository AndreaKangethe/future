"""Read-only AWS inventory connector using the optional boto3 SDK."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.connectors.base import (
    Connector,
    ConnectorConfigurationError,
    ConnectorDependencyError,
    Observation,
    normalize_observation,
)


class AWSConnector(Connector):
    source_type = "aws"
    capabilities = frozenset({"agentless-discovery", "api", "read", "scheduled"})

    def __init__(self, *, session: Any = None, region_name: str | None = None, profile_name: str | None = None):
        if session is None:
            try:
                import boto3
            except ImportError as exc:
                raise ConnectorDependencyError(
                    "AWS connector requires the optional 'boto3' package"
                ) from exc
            try:
                session = boto3.Session(region_name=region_name, profile_name=profile_name)
            except Exception as exc:
                raise ConnectorConfigurationError(f"AWS configuration is unavailable: {exc}") from exc
        self.session = session

    def validate_connectivity(self) -> None:
        try:
            self.session.client("sts").get_caller_identity()
        except Exception as exc:
            raise ConnectorConfigurationError(f"AWS credentials or endpoint are unavailable: {exc}") from exc

    def collect(self) -> Iterable[Observation]:
        yield from self._ec2()
        yield from self._vpcs()
        yield from self._security_groups()
        yield from self._rds()
        yield from self._s3()
        yield from self._elbs()

    def _observation(self, kind: str, identifiers: dict[str, Any], attributes: dict[str, Any]) -> Observation:
        return normalize_observation(
            {"asset_identifiers": identifiers, "observed_attributes": {"kind": kind, **attributes}},
            source_type=self.source_type,
            source_name="aws",
            raw_ref=f"{kind}:{next(iter(identifiers.values()), '')}",
        )

    def _ec2(self) -> Iterable[Observation]:
        for page in self.session.client("ec2").get_paginator("describe_instances").paginate():
            for reservation in page.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    yield self._observation("ec2_instance", {"instance_id": instance.get("InstanceId")}, instance)

    def _vpcs(self) -> Iterable[Observation]:
        for item in self.session.client("ec2").describe_vpcs().get("Vpcs", []):
            yield self._observation("vpc", {"vpc_id": item.get("VpcId")}, item)

    def _security_groups(self) -> Iterable[Observation]:
        for item in self.session.client("ec2").describe_security_groups().get("SecurityGroups", []):
            yield self._observation("security_group", {"group_id": item.get("GroupId")}, item)

    def _rds(self) -> Iterable[Observation]:
        for item in self.session.client("rds").describe_db_instances().get("DBInstances", []):
            yield self._observation("rds_instance", {"db_instance_id": item.get("DBInstanceIdentifier")}, item)

    def _s3(self) -> Iterable[Observation]:
        for item in self.session.client("s3").list_buckets().get("Buckets", []):
            yield self._observation("s3_bucket", {"bucket": item.get("Name")}, {"created": item.get("CreationDate")})

    def _elbs(self) -> Iterable[Observation]:
        for item in self.session.client("elbv2").describe_load_balancers().get("LoadBalancers", []):
            yield self._observation("load_balancer", {"load_balancer_arn": item.get("LoadBalancerArn")}, item)
