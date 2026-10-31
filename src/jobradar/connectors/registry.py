"""Connector plug-in registry (entry point group ``jobradar.connectors``)."""

from importlib.metadata import entry_points
from typing import Final
from urllib.parse import urlsplit

from jobradar.connectors.schemas import Connector, ConnectorsFile
from jobradar.core.source_policies import SourcePolicyRegistry

ENTRY_POINT_GROUP: Final = "jobradar.connectors"


def discover_plugins() -> dict[str, Connector]:
    """Instantiate every installed connector plug-in, keyed by its code."""
    plugins: dict[str, Connector] = {}
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        connector: Connector = entry_point.load()()
        if connector.code in plugins:
            raise ValueError(f"two connectors claim the code {connector.code}")
        plugins[connector.code] = connector
    return plugins


def check_connectors(
    connectors: dict[str, Connector], policies: SourcePolicyRegistry, config: ConnectorsFile
) -> list[str]:
    """Return every inconsistency between connectors, source policies and endpoint config.

    A connector may only call hosts it declares; every declared host must have a source policy
    that allows the connector's access mode (ADR-0022).
    """
    problems: list[str] = []
    for code, connector in sorted(connectors.items()):
        problems.extend(
            f"{code}: policy for {host} does not allow {connector.mode.value}"
            for host in connector.hosts
            if not policies.is_allowed(host, connector.mode)
        )
        settings = config.connectors.get(code)
        if settings is None:
            problems.append(f"{code}: missing from config/connectors.yaml")
            continue
        list_host = urlsplit(settings.list_url).hostname
        if list_host not in connector.hosts:
            problems.append(f"{code}: list_url host {list_host} is not one of {connector.hosts}")
    return problems
