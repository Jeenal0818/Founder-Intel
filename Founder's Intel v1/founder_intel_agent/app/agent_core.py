from openai import OpenAI

from .config import OPENAI_API_KEY, OPENROUTER_BASE_URL, TAVILY_API_KEY

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
    )
if not TAVILY_API_KEY:
    raise RuntimeError(
        "TAVILY_API_KEY is not set. Copy .env.example to .env and add your key."
    )

client = OpenAI(
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENAI_API_KEY,
)

def ask_llm(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a research agent.\n"
                    "Always answer EXACTLY in the format requested in the user message.\n"
                    "Do NOT output JSON or code blocks unless explicitly asked."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=500,
        temperature=0.2,
    )
    return response.choices[0].message.content

from tavily import TavilyClient
from typing import List, Dict, Any

tavily = TavilyClient(api_key=TAVILY_API_KEY)

def web_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_content: bool = False,
) -> List[Dict[str, Any]]:
    """
    High-level web search helper using Tavily.
    - Returns a list of dicts with url, title, snippet and optionally full content.
    - Never raises on extraction failure; just skips content for that URL.
    """
    # 1) Search the web
    resp = tavily.search(
        query=query,
        search_depth=search_depth,  # "basic" or "advanced"
        max_results=max_results,
    )

    results = resp.get("results") or []

    output = []
    for r in results:
        item = {
            "url": r.get("url"),
            "title": r.get("title"),
            "snippet": r.get("content") or r.get("snippet", ""),
        }

        # 2) Optionally try to extract full page content
        if include_content and item["url"]:
            try:
                extract_resp = tavily.extract(
                    item["url"],   # current SDK also accepts a single URL string[web:11]
                )
                # extract_resp["results"][0]["content"] for SDKs that wrap in results
                full_content = (
                    extract_resp.get("content")
                    or (extract_resp.get("results") or [{}])[0].get("content", "")
                )
                item["content"] = full_content
            except Exception as e:
                # Log and continue without content
                print(f"[extract failed] {item['url']}: {e}")
                item["content"] = ""

        output.append(item)

    return output



def fetch_page(url: str, max_chars: int = 3000, debug: bool = False) -> str:
    """
    Extract cleaned text content from a URL using Tavily Extract.
    """
    try:
        resp = tavily.extract(
            url,
            extract_depth="basic",
            output_format="text",
        )
    except Exception as e:
        if debug:
            print(f"[Tavily ERROR] extract failed for {url}: {e}")
        return ""

    # remove this in production; only show when debug=True
    if debug:
        print("[Tavily RAW]", resp)

    results = resp.get("results") or []
    failed = resp.get("failed_results") or []

    if failed:
        if debug:
            print(f"[Tavily INFO] Extraction failed for URL: {url}. Failed results: {failed}")
        return ""

    if not results:
        if debug:
            print(f"[Tavily INFO] No extractable content for: {url}")
        return ""

    doc = results[0]
    text = doc.get("raw_content") or doc.get("content") or ""
    return text[:max_chars]

def summarize(text: str) -> str:
    prompt = f"""
    Summarize the following content in bullet points:

    {text}
    """
    return ask_llm(prompt)


TOOLS = {
    "search_web": web_search,
    "fetch_page": fetch_page,
    "summarize": summarize,
}


def run_agent(goal: str, max_steps: int = 5) -> dict:
    """
    Runs the research agent.
    Returns a dict with:
      - 'trace': list of {step, thought, action, input, short_observation}
      - 'final_answer': str (full synthesized result)
    """
    memory = ""
    trace = []

    for step in range(1, max_steps + 1):
        prompt = f"""
        You are a research agent.

        Goal:
        {goal}

        Previous observations:
        {memory}

        Decide the next action.

        Available tools:
        - search_web(query: str)
        - fetch_page(url: str)
        - summarize(text: str)

        Respond in format:

        Thought: <one short sentence>
        Action: <one of: search_web, fetch_page, summarize, finish>
        Action Input: <single-line plain text, NOT JSON or code>
        Do NOT output JSON, code fences, or any other fields.
        """  # <-- CLOSES THE f-STRING

        decision = ask_llm(prompt)

        # --- parse decision ---
        thought = ""
        action = None
        action_input = None

        for raw_line in decision.split("\n"):
            line = raw_line.strip()

            if line.lower().startswith("thought:"):
                thought = line.split("Thought:", 1)[1].strip()

            elif line.lower().startswith("action:"):
                action = line.split("Action:", 1)[1].strip()
                action = action.split("(")[0].strip().strip('"').strip("'")

            elif line.lower().startswith("action input:"):
                action_input = line.split("Action Input:", 1)[1].strip()
                if (
                    (action_input.startswith('"') and action_input.endswith('"')) or
                    (action_input.startswith("'") and action_input.endswith("'"))
                ):
                    action_input = action_input[1:-1].strip()

        if not action or action.lower() == "finish":
            break

        if action not in TOOLS:
            # stop gracefully on unknown action
            break

        # --- execute tool (hidden from final user view) ---
        try:
            result = TOOLS[action](action_input)
        except Exception as e:
            result = f"[Tool error in {action}: {e}]"

        # Short observation kept for memory and trace, but not full raw page.
        if isinstance(result, str):
            short_obs = result[:300]
        else:
            short_obs = str(result)[:300]

        memory += f"\nThought: {thought}\nAction: {action}\nObservation: {short_obs}\n"

        trace.append(
            {
                "step": step,
                "thought": thought,
                "action": action,
                "input": action_input,
                "observation": short_obs,
            }
        )

    # --- final answer: ask LLM to synthesize using memory ---
    final_prompt = f"""
    You are a research assistant.

    Goal:
    {goal}

    Research log:
    {memory}

    Produce a clean, well-structured final answer for the user.
    Do NOT list tool calls or URLs. Just present the conclusions.
    """

    final_answer = ask_llm(final_prompt)

    return {
        "trace": trace,
        "final_answer": final_answer,
    }


def extract_structured_events_from_brief(brief: str) -> List[Dict[str, Any]]:
    """
    Very simple placeholder that turns each non-empty line in the brief
    into a generic event dict. This avoids runtime errors when
    downstream code expects a list of events.
    """
    events: List[Dict[str, Any]] = []
    for raw_line in brief.splitlines():
        line = raw_line.strip("- ").strip()
        if not line:
            continue
        events.append(
            {
                "type": "other",
                "competitor": "",
                "summary": line,
                "severity": "medium",
                "confidence": 70,
            }
        )
    return events

def tool_competitor_research(goal: str) -> dict:
    """
    High-level tool:
      - runs research
      - produces founder brief
      - extracts structured events
      - classifies which are critical vs weekly
    """
    result = run_agent(goal, max_steps=4)

    synthesis_prompt = f"""
    You are a startup strategy analyst.

    Goal:
    {goal}

    Internal research trace:
    {result['trace']}

    Write a concise intelligence brief for a founder:
    - 3–7 bullet points
    - Sections: Competitor Moves, Market Signals, Suggested Actions
    - ONLY describe events that clearly happened within the last 7 days (this week).
    - If an article or source looks older than 7 days (e.g. dated 2024 or earlier), ignore it.
    - No tool calls, no URLs, no internal reasoning.
    """
    brief = ask_llm(synthesis_prompt)

    events = extract_structured_events_from_brief(brief)
    buckets = classify_alerts(events)

    return {
        "brief": brief,
        "events": events,
        "critical_events": buckets["critical"],
        "weekly_events": buckets["weekly"],
    }

from typing import List, Dict, Any

IntelEvent = Dict[str, Any]


def classify_alerts(events: List[IntelEvent]) -> Dict[str, List[IntelEvent]]:
    """
    Split events into:
      - 'critical': send immediate alerts
      - 'weekly': include in weekly summary only
    Simple rule-based logic for now.
    """
    critical: List[IntelEvent] = []
    weekly: List[IntelEvent] = []

    for ev in events:
        etype = ev.get("type", "other")
        sev = ev.get("severity", "medium")
        conf = ev.get("confidence", 70)

        is_critical = False

        # Critical when high-impact + reasonably confident
        if etype in {"pricing_change", "feature_launch", "funding_round", "market_entry"}:
            if sev == "high" and conf >= 70:
                is_critical = True

        # Everything else goes to weekly digest
        if is_critical:
            critical.append(ev)
        else:
            weekly.append(ev)

    return {"critical": critical, "weekly": weekly}

#Company registering

from typing import List, Dict, Any

CompanyConfig = Dict[str, Any]

COMPANIES: Dict[str, CompanyConfig] = {}


def format_weekly_email(res: dict) -> str:
    """
    Turn monitoring result into a plain-text weekly email body for founders.
    """
    lines = []

    lines.append(f"Weekly Intelligence Brief – {res['company_name']}")
    lines.append("")
    lines.append("=== Executive Summary ===")
    lines.append(res["brief"].strip())
    lines.append("")

    if res.get("critical_events"):
        lines.append("=== Critical Moves (This Week) ===")
        for ev in res["critical_events"]:
            lines.append(
                f"- [{ev['type']}] {ev['competitor']}: {ev['summary']} "
                f"(severity: {ev['severity']}, confidence: {ev['confidence']})"
            )
        lines.append("")

    lines.append("")
    lines.append(
        "This report was generated automatically by competitor intelligence agent."
    )

    return "\n".join(lines)


def format_critical_email(res: dict) -> str:
    """
    Turn monitoring result into a plain-text critical alert email body.
    Focused only on critical events.
    """
    lines = []

    lines.append(f"Critical Competitor Moves – {res['company_name']}")
    lines.append("")
    lines.append("The following critical events were detected:")
    lines.append("")

    if res.get("critical_events"):
        for ev in res["critical_events"]:
            lines.append(
                f"- [{ev['type']}] {ev['competitor']}: {ev['summary']} "
                f"(severity: {ev['severity']}, confidence: {ev['confidence']})"
            )
    else:
        lines.append("- No critical events found, but this email was triggered.")

    lines.append("")
    lines.append(
        "This alert was generated automatically by your competitor intelligence agent."
    )

    return "\n".join(lines)


def generate_strategic_recommendations(company_id: str, res: dict) -> str:
    """
    Use the brief and structured events to propose concrete strategic recommendations
    for the founder. Returns plain-text bullet points.
    """
    brief = res.get("brief", "")
    events = res.get("events", [])

    prompt = f"""
You are a startup strategy advisor.

Company ID: {company_id}

Intelligence brief (already filtered to the last 7 days):
{brief}

Structured events (already filtered to the last 7 days):
{events}

Write 3–7 concrete, actionable strategic recommendations for the founder.
Focus on what they should DO in the next 1–4 weeks, based ONLY on events from the last 7 days.
Do NOT base recommendations on older historical context.
Return plain text bullet points only (no headings, no numbering metadata).
"""
    return ask_llm(prompt)