# app/monitoring_service.py
from typing import Optional
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import MonitoringRun, RunType
from .company_service import get_company
from .agent_core import tool_competitor_research, format_weekly_email, format_critical_email
from .emailer import send_intel_email


def _log_run(
    company_id: str,
    run_type: RunType,
    res: dict,
    session: Optional[Session] = None,
):
    own_session = False
    if session is None:
        session = SessionLocal()
        own_session = True
    try:
        run = MonitoringRun(
            company_id=company_id,
            run_type=run_type,
            brief=res.get("brief"),
            events=res.get("events", []),
            critical_events=res.get("critical_events", []),
            weekly_events=res.get("weekly_events", []),
            recommendations=res.get("recommendations", ""),
        )
        session.add(run)
        session.commit()
    finally:
        if own_session:
            session.close()


def run_company_monitoring(company_id: str) -> dict:
    company = get_company(company_id)
    if company is None:
        raise ValueError(f"Unknown company_id: {company_id}")

    competitors = ", ".join(company.competitors)
    market_keywords = ", ".join(company.market_keywords)

    goal = (
        f"Monitor {competitors} and the broader {market_keywords} market on behalf of {company.name}. "
        f"Focus on pricing changes, new features, product launches, funding rounds, "
        f"hiring spikes, and market entry or positioning shifts. "
        f"ONLY include events that clearly occurred within the last 7 days and ignore older news, "
        f"even if search results surface them. Summarize only the most important moves that affect "
        f"{company.name}'s strategy."
    )

    res = tool_competitor_research(goal)
    res = {
        "company_id": company_id,
        "company_name": company.name,
        **res,
    }
    return res


def send_weekly_intel(company_id: str):
    company = get_company(company_id)
    if company is None:
        raise ValueError(f"Unknown company_id: {company_id}")

    res = run_company_monitoring(company_id)

    # generate strategy-aware recommendations inside agent_core
    from .agent_core import generate_strategic_recommendations

    recs = generate_strategic_recommendations(company_id, res)
    res["recommendations"] = recs

    body = format_weekly_email(res)
    subject = f"Weekly Intelligence – {res['company_name']}"

    send_intel_email(subject, body, company.founders_emails)
    _log_run(company_id, RunType.weekly, res)


def send_daily_critical_intel(company_id: str):
    company = get_company(company_id)
    if company is None:
        raise ValueError(f"Unknown company_id: {company_id}")

    res = run_company_monitoring(company_id)

    if not res.get("critical_events"):
        _log_run(company_id, RunType.daily_critical, res)
        return

    body = format_critical_email(res)
    subject = f"Critical Competitor Moves – {res['company_name']}"
    send_intel_email(subject, body, company.founders_emails)

    _log_run(company_id, RunType.daily_critical, res)
