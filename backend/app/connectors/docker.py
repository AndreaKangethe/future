"""Read-only Docker Engine connector."""

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


class DockerConnector(Connector):
    source_type = "docker"
    capabilities = frozenset({"agentless-discovery", "api", "read"})

    def __init__(self, *, client: Any = None, enabled: bool = True) -> None:
        if not enabled:
            raise ConnectorConfigurationError("Docker connector is disabled; set enabled=True to opt in")
        if client is None:
            try:
                import docker
            except ImportError as exc:
                raise ConnectorDependencyError(
                    "Docker connector requires the optional 'docker' package"
                ) from exc
            try:
                client = docker.from_env()
            except Exception as exc:
                raise ConnectorConfigurationError(
                    f"Docker Engine is unavailable: {exc}"
                ) from exc
        self.client = client

    def validate_connectivity(self) -> None:
        try:
            self.client.version()
        except Exception as exc:
            raise ConnectorConfigurationError(f"Docker Engine is unavailable: {exc}") from exc

    def collect(self) -> Iterable[Observation]:
        for container in self.client.containers.list(all=True):
            attrs = getattr(container, "attrs", {}) or {}
            config = attrs.get("Config", {}) or {}
            state = attrs.get("State", {}) or {}
            network_settings = attrs.get("NetworkSettings", {}) or {}
            identifiers = {"container_id": getattr(container, "id", None)}
            name = getattr(container, "name", None) or config.get("Hostname")
            if name:
                identifiers["hostname"] = name
            attributes = {
                "kind": "container",
                "image": config.get("Image"),
                "state": state.get("Status") or getattr(container, "status", None),
                "ports": network_settings.get("Ports", {}),
                "labels": config.get("Labels", {}),
            }
            yield normalize_observation(
                {"asset_identifiers": identifiers, "observed_attributes": attributes},
                source_type=self.source_type,
                source_name="docker",
                raw_ref=f"container:{getattr(container, 'id', '')}",
            )

        for image in self.client.images.list():
            attrs = getattr(image, "attrs", {}) or {}
            image_id = getattr(image, "id", None) or attrs.get("Id")
            yield normalize_observation(
                {
                    "asset_identifiers": {"image_id": image_id},
                    "observed_attributes": {
                        "kind": "image",
                        "tags": getattr(image, "tags", []),
                        "size": attrs.get("Size"),
                    },
                },
                source_type=self.source_type,
                source_name="docker",
                raw_ref=f"image:{image_id or ''}",
            )
