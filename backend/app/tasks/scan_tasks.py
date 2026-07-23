from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.models.finding import Finding
from app.models.report import Report
from app.models.scan import STATUS_COMPLETED, STATUS_FAILED, STATUS_RUNNING, Scan
from app.models.target import Target
from app.services.ai.report_generator import generate_report
from app.services.scanners import headers_tls, recon, webvuln
from app.tasks.celery_app import celery_app

SCANNER_MODULES = {
    "recon": recon.run,
    "headers_tls": headers_tls.run,
    "webvuln": webvuln.run,
}


@celery_app.task(name="run_scan_task")
def run_scan_task(scan_id: int) -> None:
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if scan is None:
            return
        target = db.query(Target).filter(Target.id == scan.target_id).first()

        scan.status = STATUS_RUNNING
        scan.started_at = datetime.now(timezone.utc)
        db.commit()

        try:
            all_findings: list[dict] = []
            for module_name in scan.modules:
                scanner_fn = SCANNER_MODULES.get(module_name)
                if scanner_fn is None:
                    continue
                all_findings.extend(scanner_fn(target.domain))

            previous_scan = (
                db.query(Scan)
                .filter(
                    Scan.target_id == scan.target_id,
                    Scan.status == STATUS_COMPLETED,
                    Scan.id != scan.id,
                    Scan.created_at < scan.created_at,
                )
                .order_by(Scan.created_at.desc())
                .first()
            )

            trend_context = None
            if previous_scan is not None:
                previous_keys = {f.key for f in previous_scan.findings}
                current_keys = {f.get("key", f["title"]) for f in all_findings}
                new_count = len(current_keys - previous_keys)
                resolved_count = len(previous_keys - current_keys)
                trend_context = (
                    f"Onceki tarama ({previous_scan.created_at.date()}) ile kiyaslandiginda "
                    f"{new_count} yeni bulgu tespit edildi, {resolved_count} bulgu artik gorunmuyor "
                    f"(kapatilmis olabilir). Onceki risk skoru: {previous_scan.risk_score}."
                )

            for f in all_findings:
                db.add(
                    Finding(
                        scan_id=scan.id,
                        module=f["module"],
                        key=f.get("key", f["title"]),
                        severity=f["severity"],
                        title=f["title"],
                        description=f.get("description", ""),
                        evidence=f.get("evidence", {}),
                    )
                )
            db.commit()

            report_data = generate_report(target.domain, all_findings, trend_context)
            db.add(
                Report(
                    scan_id=scan.id,
                    risk_score=report_data["risk_score"],
                    executive_summary=report_data["executive_summary"],
                    technical_summary=report_data["technical_summary"],
                    prioritized_findings=report_data["prioritized_findings"],
                )
            )

            scan.risk_score = report_data["risk_score"]
            scan.status = STATUS_COMPLETED
            scan.finished_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as exc:  # noqa: BLE001 - isolate scan failures per-scan
            db.rollback()
            scan.status = STATUS_FAILED
            scan.error_message = str(exc)[:1000]
            scan.finished_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()
