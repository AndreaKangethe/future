import asyncio
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.core import Asset, Finding
from app.models.observation import Observation, Source, observation_hash
from app.pipeline.observation import normalize_identifiers, quality_flags, quality_score


async def main():
    async with SessionLocal() as db:
        if await db.scalar(select(Asset).limit(1)):
            return
        random.seed(42)
        asset_types = [
            "server",
            "workstation",
            "network_device",
            "cloud_resource",
            "vm",
            "container",
            "application",
        ]
        assets = [
            Asset(
                name="app-server-01",
                asset_type="server",
                criticality=5,
                exposure_status="external",
                identity_confidence=0.96,
                epistemic_class="confirmed",
            ),
            Asset(
                name="db-prod-01",
                asset_type="server",
                criticality=5,
                exposure_status="internal",
                identity_confidence=0.99,
                epistemic_class="confirmed",
            ),
            Asset(
                name="edge-router-01",
                asset_type="network_device",
                criticality=4,
                exposure_status="external",
                identity_confidence=0.91,
                epistemic_class="normalized",
            ),
        ] + [
            Asset(
                name=f"{asset_type.replace('_', '-')}-{index:03d}",
                asset_type=asset_type,
                criticality=random.randint(1, 5),
                exposure_status="external" if index % 7 == 0 else "internal",
                identity_confidence=round(random.uniform(0.55, 0.99), 2),
                epistemic_class="normalized",
            )
            for index in range(4, 321)
            for asset_type in [asset_types[index % len(asset_types)]]
        ]
        db.add_all(assets)
        await db.flush()
        db.add_all(
            [
                Finding(
                    asset_id=assets[0].id,
                    title="Internet-exposed service requires verification",
                    severity="critical",
                    cvss_score=9.8,
                    contextual_risk=94,
                    epistemic_class="assessed",
                ),
                Finding(
                    asset_id=assets[1].id,
                    title="Outdated database component",
                    severity="high",
                    cvss_score=8.1,
                    contextual_risk=76,
                    epistemic_class="observed",
                ),
                *[
                    Finding(
                        asset_id=asset.id,
                        title="Service exposure changed",
                        severity="high" if asset.exposure_status == "external" else "medium",
                        cvss_score=7.5 if asset.exposure_status == "external" else 5.4,
                        contextual_risk=round(random.uniform(35, 88), 1),
                        epistemic_class="assessed",
                    )
                    for asset in assets[3::19]
                ],
            ]
        )
        source = Source(name="demo-synthetic", source_type="demo", reliability=0.9)
        db.add(source)
        await db.flush()
        observations = []
        for day in range(30):
            timestamp = datetime.now(UTC) - timedelta(days=day)
            for asset in assets[::10]:
                identifiers = normalize_identifiers(
                    {"hostname": asset.name, "ip": f"192.0.2.{(assets.index(asset) % 240) + 1}"}
                )
                flags = quality_flags(identifiers, timestamp, source_verified=True)
                observations.append(
                    Observation(
                        source_id=source.id,
                        source_type="demo",
                        observation_category="asset",
                        asset_identifiers=identifiers,
                        observed_attributes={"asset_type": asset.asset_type, "day": day},
                        observation_timestamp=timestamp,
                        collection_timestamp=datetime.now(UTC),
                        processing_status="resolved",
                        quality_flags=flags,
                        quality_score=quality_score(flags),
                        epistemic_class="observed",
                        dedup_hash=observation_hash(
                            source.id, "asset", identifiers, {"day": day}, timestamp
                        ),
                    )
                )
        db.add_all(observations)
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
