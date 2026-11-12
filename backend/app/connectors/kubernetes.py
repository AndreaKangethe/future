"""Read-only Kubernetes connector."""

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


class KubernetesConnector(Connector):
    source_type = "kubernetes"
    capabilities = frozenset({"agentless-discovery", "api", "read", "scheduled"})

    def __init__(self, *, client: Any = None, config_file: str | None = None, in_cluster: bool = False):
        if client is None:
            try:
                from kubernetes import client as kube_client
                from kubernetes import config
            except ImportError as exc:
                raise ConnectorDependencyError(
                    "Kubernetes connector requires the optional 'kubernetes' package"
                ) from exc
            try:
                if in_cluster:
                    config.load_incluster_config()
                else:
                    config.load_kube_config(config_file=config_file)
                client = kube_client
            except Exception as exc:
                raise ConnectorConfigurationError(
                    f"Kubernetes configuration is unavailable: {exc}"
                ) from exc
        self.client = client

    def validate_connectivity(self) -> None:
        try:
            self.client.CoreV1Api().list_namespace(_request_timeout=5)
        except Exception as exc:
            raise ConnectorConfigurationError(f"Kubernetes API is unavailable: {exc}") from exc

    def collect(self) -> Iterable[Observation]:
        core = self.client.CoreV1Api()
        apps = self.client.AppsV1Api()
        for item in core.list_node().items:
            yield self._resource("node", item, {"name": item.metadata.name})
        for item in core.list_pod_for_all_namespaces().items:
            yield self._resource(
                "pod", item, {"name": item.metadata.name, "namespace": item.metadata.namespace}
            )
        for item in core.list_service_for_all_namespaces().items:
            yield self._resource(
                "service", item, {"name": item.metadata.name, "namespace": item.metadata.namespace}
            )
        for item in core.list_namespace().items:
            yield self._resource("namespace", item, {"name": item.metadata.name})
        for item in apps.list_deployment_for_all_namespaces().items:
            yield self._resource(
                "deployment",
                item,
                {"name": item.metadata.name, "namespace": item.metadata.namespace},
            )

    def _resource(self, kind: str, item: Any, identifiers: dict[str, Any]) -> Observation:
        metadata = getattr(item, "metadata", None)
        return normalize_observation(
            {
                "asset_identifiers": {"kubernetes_uid": getattr(metadata, "uid", None), **identifiers},
                "observed_attributes": {
                    "kind": kind,
                    "labels": getattr(metadata, "labels", {}) or {},
                },
            },
            source_type=self.source_type,
            source_name="kubernetes",
            raw_ref=f"{kind}:{getattr(metadata, 'uid', '')}",
        )
