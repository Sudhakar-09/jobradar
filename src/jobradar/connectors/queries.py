"""Aggregator query planning from packs (pure; no I/O)."""

from collections.abc import Sequence

from jobradar.connectors.schemas import SourceQuery
from jobradar.core.packs import MarketPack, RolePack


def plan_queries(
    markets: Sequence[MarketPack], roles: Sequence[RolePack]
) -> tuple[SourceQuery, ...]:
    """One query per (country market, role): the role's title aliases are the search terms.

    The job corpus is shared, so queries cover every configured market and role rather than one
    user's targets; matching narrows them per user later. Region markets (no single country)
    are not searched by country-based aggregators.
    """
    return tuple(
        SourceQuery(
            market=market.code,
            country=market.country_codes[0],
            role=role.code,
            field=role.field,
            terms=tuple(role.title_aliases),
        )
        for market in markets
        if market.kind == "country"
        for role in roles
    )
