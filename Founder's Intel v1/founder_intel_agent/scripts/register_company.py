from founder_intel_agent.app.company_service import register_company

register_company(
    company_id="notion",
    company_name="Notion",
    competitors=["Evernote", "Coda", "ClickUp", "Google Docs"],
    founders_emails=["jinaljain1918@gmail.com"],
    market_keywords=["productivity", "workspace", "note-taking", "project management"],
    strategy_note=(
        "Track major product launches, pricing changes, enterprise features, and AI "
        "workflow announcements from key productivity and collaboration competitors."
    ),
)
