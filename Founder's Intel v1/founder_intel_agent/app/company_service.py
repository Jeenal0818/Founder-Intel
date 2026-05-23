# app/company_service.py
from typing import List, Optional
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import Company


def register_company(
    company_id: str,
    company_name: str,
    competitors: List[str],
    founders_emails: List[str],
    market_keywords: List[str],
    strategy_note: str = "",
    session: Optional[Session] = None,
):
    own_session = False
    if session is None:
        session = SessionLocal()
        own_session = True

    try:
        company = session.get(Company, company_id)
        if company is None:
            company = Company(
                id=company_id,
                name=company_name,
                competitors=competitors,
                founders_emails=founders_emails,
                market_keywords=market_keywords,
                strategy_note=strategy_note,
            )
            session.add(company)
        else:
            company.name = company_name
            company.competitors = competitors
            company.founders_emails = founders_emails
            company.market_keywords = market_keywords
            company.strategy_note = strategy_note
        session.commit()
    finally:
        if own_session:
            session.close()


def get_company(company_id: str, session: Optional[Session] = None) -> Company:
    own_session = False
    if session is None:
        session = SessionLocal()
        own_session = True
    try:
        company = session.get(Company, company_id)
        return company
    finally:
        if own_session:
            session.close()
