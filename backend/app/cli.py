import argparse
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.session import create_database_engine
from app.models import (
    DataQualitySnapshot,
    Dataset,
    DatasetImport,
    DataSource,
    IngestionJob,
    IngestionRecord,
    Location,
    Organisation,
    PipelineRun,
    Programme,
)


def _seed_demo(session: Session) -> None:
    tables = (
        Organisation, Location, Programme, DataSource, Dataset, DatasetImport, PipelineRun,
        DataQualitySnapshot, IngestionRecord, IngestionJob,
    )
    if any(session.scalar(select(func.count()).select_from(table)) for table in tables):
        raise SystemExit("Demo seeding requires empty business tables; no changes were made.")

    now = datetime.now(UTC)
    sources = [
        DataSource(name="School Attendance Demo", source_type="CSV", records_count=18400),
        DataSource(name="Youth Placement Demo", source_type="API", records_count=9200),
        DataSource(name="Community Health Demo", source_type="CSV", records_count=12750),
    ]
    session.add_all(sources)
    session.flush()

    programmes = [
        Programme(
            name="Learning Support Demo",
            category="Education",
            province="Gauteng",
            target_beneficiaries=5000,
            reached_beneficiaries=3780,
        ),
        Programme(
            name="Youth Employment Demo",
            category="Employment",
            province="KwaZulu-Natal",
            target_beneficiaries=3200,
            reached_beneficiaries=2410,
        ),
        Programme(
            name="Community Health Demo",
            category="Healthcare",
            province="Eastern Cape",
            target_beneficiaries=4100,
            reached_beneficiaries=2990,
        ),
        Programme(
            name="Skills for Work Demo",
            category="Community Development",
            province="Western Cape",
            target_beneficiaries=2600,
            reached_beneficiaries=2015,
        ),
    ]
    session.add_all(programmes)

    for day in range(6):
        event_time = now - timedelta(days=day)
        source = sources[day % len(sources)]
        session.add(
            PipelineRun(
                pipeline_name=f"Demo metadata run {day + 1}",
                source_id=source.id,
                status=("succeeded", "succeeded", "running", "failed", "warning", "succeeded")[
                    day
                ],
                records_processed=700 + day * 113,
                started_at=event_time,
                completed_at=event_time + timedelta(minutes=4)
                if day != 2
                else None,
            )
        )
        session.add(
            IngestionRecord(
                source_id=source.id,
                records_ingested=500 + day * 79,
                ingested_at=event_time,
            )
        )
    for week in range(4):
        session.add(
            DataQualitySnapshot(
                score=92.5 + week * 1.1,
                checked_at=now - timedelta(weeks=3 - week),
            )
        )

    session.commit()
    print("Synthetic demo records created. No individual beneficiary records were added.")


def main() -> None:
    parser = argparse.ArgumentParser(description="ImpactFlow backend utilities")
    parser.add_argument("command", choices=["seed-demo"])
    parser.parse_args()
    settings = Settings()
    if not settings.database_url:
        raise SystemExit("Set IMPACTFLOW_DATABASE_URL before running this command.")

    engine = create_database_engine(settings.database_url)
    try:
        with Session(engine) as session:
            _seed_demo(session)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
