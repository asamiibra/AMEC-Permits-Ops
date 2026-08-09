from sqlalchemy import select
from ..db import SessionLocal, init_db
from ..models import DatasetType, ExtractionSpikeRun
from ..services.spike import run_spike


def main():
    init_db()
    with SessionLocal() as db:
        run = ExtractionSpikeRun(dataset_name="Synthetic Week 2 Worst-Case Corpus", dataset_type=DatasetType.SYNTHETIC, environment="TEST", extractor_config_version="LOCAL-SYNTHETIC-EXTRACTOR-1.0", classifier_config_version="RULES-W2-1.0", notes="Synthetic harness validation; not real-document testing.")
        db.add(run); db.flush(); run_spike(db, run, "synthetic-spike-cli"); db.commit()
        print({"id": run.id, "documents": run.document_count, "metrics": run.metrics_json})


if __name__ == "__main__": main()
