import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.core import Asset, Finding


async def main():
    async with SessionLocal() as db:
        if await db.scalar(select(Asset).limit(1)):
            return
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
            ]
        )
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
