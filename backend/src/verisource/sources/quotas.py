"""Free request/token/concurrency reservations and the fixed application limits.

Application limits never masquerade as provider quota, and no monetary tariff is needed for
free pages or local files. Provider quota (for example an eligible free Gemini project) is
read from configuration; no free allowance is ever assumed.
"""

import zlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from verisource.db.models import BudgetReservation


@dataclass(frozen=True)
class Limits:
    active_batch_suppliers: int = 5
    global_requests: int = 4
    per_domain_requests: int = 1
    browser_sessions: int = 1
    pages_per_supplier: int = 20
    certificate_pdfs_per_supplier: int = 5
    crawl_depth: int = 2
    request_timeout_seconds: int = 20
    transient_retries: int = 1
    website_deadline_seconds: int = 15 * 60
    initial_report_seconds: int = 30 * 60
    model_concurrency: int = 1
    model_context_tokens: int = 4096


LIMITS = Limits()


def budgets_json() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "paid_spend_limit": 0,
        "requests": {
            "global": LIMITS.global_requests,
            "per_domain": LIMITS.per_domain_requests,
            "browser": LIMITS.browser_sessions,
        },
        "per_supplier": {
            "pages": LIMITS.pages_per_supplier,
            "certificate_pdfs": LIMITS.certificate_pdfs_per_supplier,
            "depth": LIMITS.crawl_depth,
        },
        "timeout_seconds": LIMITS.request_timeout_seconds,
        "transient_retries": LIMITS.transient_retries,
        "website_deadline_seconds": LIMITS.website_deadline_seconds,
        "model": {
            "concurrency": LIMITS.model_concurrency,
            "context_tokens": LIMITS.model_context_tokens,
        },
    }


def reserve(
    db: Session,
    *,
    case_id: UUID,
    run_id: UUID,
    consumer: str,
    unit: str,
    amount: int,
    operation_key: str,
    cycle: str | None = None,
    limit: int | None = None,
    provider_account_id: UUID | None = None,
) -> BudgetReservation | None:
    """Atomically reserve free quota; returns None (quota_exhausted) when it would exceed it.

    `limit` is the actual configured project allowance for the cycle. When no limit is
    configured the caller must not call this for a provider (no invented allowance).
    """
    existing = db.scalar(
        select(BudgetReservation).where(
            BudgetReservation.case_id == case_id, BudgetReservation.operation_key == operation_key
        )
    )
    if existing is not None:
        return existing
    if limit is not None:
        db.execute(select(func.pg_advisory_xact_lock(zlib.crc32(f"{unit}:{cycle}".encode()))))
        used = int(
            db.scalar(
                select(func.coalesce(func.sum(BudgetReservation.reserved_amount), 0)).where(
                    BudgetReservation.unit == unit,
                    BudgetReservation.cycle == cycle,
                    BudgetReservation.provider_account_id == provider_account_id,
                    BudgetReservation.state.in_(("reserved", "settled")),
                )
            )
            or 0
        )
        if used + amount > limit:
            return None
    reservation = BudgetReservation(
        provider_account_id=provider_account_id,
        run_id=run_id,
        case_id=case_id,
        consumer=consumer,
        unit=unit,
        reserved_amount=amount,
        cycle=cycle,
        operation_key=operation_key,
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )
    db.add(reservation)
    db.flush()
    return reservation


def settle(reservation: BudgetReservation, actual: int) -> None:
    reservation.settled_amount = actual
    reservation.state = "settled"
