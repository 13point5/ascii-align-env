import asyncio
import json
import os
import random
from typing import Dict, List

from dotenv import load_dotenv
from openai import AsyncOpenAI
from tqdm import tqdm

load_dotenv()

# -----------------------------
# Config
# -----------------------------
TOTAL_TASKS = 7000
CONCURRENCY = 20
OUT_JSONL = "prompts_7k.jsonl"
MODEL = "gpt-4.1-mini"
API_KEY = os.getenv("OPENAI_API_KEY", "")

# -----------------------------
# Themes (equal sampling)
# -----------------------------
THEMES = [
    {
        "name": "flowcharts",
        "description": "Procedural flowcharts with decisions, loops, and error paths. Clear step labels. Human-like phrasing.",
        "examples": [
            "Draw a flowchart for a password reset flow with an expired-token error path.",
            "Create a flowchart for a checkout process that includes coupon validation and payment failure retry.",
            "Make a flowchart for an incident response runbook: detect → triage → mitigate → postmortem, with an escalation decision.",
        ],
    },
    {
        "name": "architecture",
        "description": "System architecture diagrams: components, data stores, queues, services, arrows indicating data/control flow.",
        "examples": [
            "Draw a web app architecture with client, API, Redis queue, workers, and a Postgres database.",
            "Create an ML inference architecture: request API → feature store → model server → metrics/logging sink.",
            "Draw a CI/CD architecture: repo → CI runner → artifact store → deploy controller → cluster.",
        ],
    },
    {
        "name": "sequence",
        "description": "Sequence diagrams: participants (lifelines), messages, optional success/failure branches described in text.",
        "examples": [
            "Draw a sequence diagram for login: client → API → auth DB → session store, then back to client.",
            "Create a sequence diagram for file upload: client, API, object storage, virus scanner, metadata DB.",
            "Draw a sequence diagram for data export: user triggers export, job is queued, worker generates file, user downloads.",
        ],
    },
    {
        "name": "state_machines",
        "description": "State machine diagrams: states and transitions with events/conditions.",
        "examples": [
            "Draw a state machine for an order: created → paid → shipped → delivered, with cancel/return branches.",
            "Create a subscription lifecycle state machine: trial, active, past_due, canceled, resumed.",
            "Draw a job state machine: queued, running, succeeded, failed, retried.",
        ],
    },
]

# -----------------------------
# Diversity controls
# -----------------------------
TECH_DOMAINS = [
    "payments platform",
    "identity and access management",
    "observability stack",
    "CI/CD pipeline",
    "feature flag service",
    "notifications system",
    "data ingestion pipeline",
    "ETL workflow",
    "stream processing service",
    "real-time analytics",
    "ML training pipeline",
    "model serving",
    "A/B testing platform",
    "search and indexing",
    "recommendation system",
    "edge caching",
    "video transcoding",
    "IoT device fleet",
    "multi-tenant SaaS app",
    "incident response",
    "security monitoring",
    "backup and restore",
    "auth + SSO",
    "rate limiting and throttling",
    "billing and invoicing",
    "customer support automation",
    "fraud detection",
    "log aggregation",
    "workflow orchestration",
    "data governance",
]

TECH_PROCESSES = [
    "request handling flow",
    "failure recovery path",
    "provisioning workflow",
    "deployment pipeline",
    "rollout strategy",
    "data validation pipeline",
    "alerting workflow",
    "sync process",
    "batch job lifecycle",
    "approval workflow",
    "rate-limit handling",
    "caching strategy",
    "retry strategy",
    "data export process",
    "incident escalation",
    "feature rollout",
    "multi-region failover",
    "disaster recovery",
]

TECH_ARTIFACTS = [
    "API gateway",
    "queue",
    "worker",
    "database",
    "cache",
    "object storage",
    "dashboard",
    "job scheduler",
    "message bus",
    "vector database",
    "feature store",
    "auth service",
    "audit log",
    "metrics pipeline",
]

NONTECH_DOMAINS = [
    "travel planning",
    "restaurant operations",
    "hospital intake",
    "school enrollment",
    "library checkouts",
    "event planning",
    "real estate listing",
    "manufacturing line",
    "supply chain",
    "fitness coaching",
    "personal finance budgeting",
    "construction project",
    "customer service desk",
    "museum exhibit flow",
    "film production",
]

NONTECH_PROCESSES = [
    "approval process",
    "booking flow",
    "check-in flow",
    "order fulfillment",
    "handoff process",
    "inventory reconciliation",
    "staff scheduling",
    "incident handling",
    "quality review",
    "change request",
]

AUDIENCES = [
    "new hires",
    "engineers",
    "product managers",
    "executives",
    "support agents",
    "customers",
    "students",
]

DETAIL_LEVELS = [
    "high level",
    "medium detail",
    "low level with edge cases",
]

STYLES = [
    "concise labels",
    "clear step names",
    "human-friendly phrasing",
    "short sentences",
]

CONSTRAINTS = [
    "Include at least one decision and one error path.",
    "Include a retry loop and a timeout.",
    "Include a manual review step.",
    "Include a metrics or logging step.",
    "Show data flow and control flow distinctly.",
    "Include a rollback or recovery branch.",
    "Include a security check or authorization step.",
    "Include a dependency on an external system.",
]

OUTPUT_RULES = [
    "The output should just be plain text, no JSON or other formatting.",
    "It should be a single sentence or short paragraph that describes the diagram request.",
    "The tone of the output should be like a user prompt that a human would write to an LLM to draw a diagram.",
]

SHAPE_BUDGETS = [4, 6, 8, 10, 12, 16, 20]


def get_example_prompts() -> List[str]:
    return [example for theme in THEMES for example in theme["examples"]]


def complexity_hint(budget: int) -> str:
    if budget <= 4:
        return "tiny and very simple"
    if budget <= 6:
        return "small and simple"
    if budget <= 8:
        return "compact and focused"
    if budget <= 10:
        return "medium complexity"
    if budget <= 12:
        return "moderately complex"
    if budget <= 16:
        return "complex but still readable"
    return "very complex but still readable"


def build_use_cases() -> List[str]:
    tech = [
        f"{process} for {domain} involving {artifact}"
        for domain in TECH_DOMAINS
        for process in TECH_PROCESSES
        for artifact in TECH_ARTIFACTS
    ]
    nontech = [
        f"{process} for {domain}" for domain in NONTECH_DOMAINS for process in NONTECH_PROCESSES
    ]
    return tech, nontech


TECH_USE_CASES, NONTECH_USE_CASES = build_use_cases()

USE_CASES = TECH_USE_CASES + NONTECH_USE_CASES
USE_CASE_WEIGHTS = [5.0] * len(TECH_USE_CASES) + [1.0] * len(NONTECH_USE_CASES)


def sample_row() -> Dict[str, str]:
    theme = random.choice([t["name"] for t in THEMES])
    use_case = random.choices(USE_CASES, weights=USE_CASE_WEIGHTS, k=1)[0]
    audience = random.choice(AUDIENCES)
    detail_level = random.choice(DETAIL_LEVELS)
    style = random.choice(STYLES)
    constraint = random.choice(CONSTRAINTS)
    output_rule = random.choice(OUTPUT_RULES)
    shape_budget = random.choice(SHAPE_BUDGETS)
    hint = complexity_hint(shape_budget)

    return {
        "theme": theme,
        "use_case": use_case,
        "audience": audience,
        "detail_level": detail_level,
        "style": style,
        "constraint": constraint,
        "output_rule": output_rule,
        "shape_budget": shape_budget,
        "complexity_hint": hint,
    }


def build_meta_prompt(row: Dict[str, str], examples: str) -> str:
    return (
        "Generate a user prompt asking an LLM to draw a {theme} diagram."
        "Use a different use case when compared to the examples."
        "The prompt should be for: {use_case}."
        "Audience: {audience}. Detail level: {detail_level}. Style: {style}."
        "Keep the diagram {complexity_hint} with an appropriate number of entities and connections."
        "{constraint} {output_rule}"
        f"\nExamples:\n{examples}"
    ).format(**row)


async def generate_one(
    client: AsyncOpenAI, examples: str, semaphore: asyncio.Semaphore
) -> Dict[str, str]:
    row = sample_row()
    prompt = build_meta_prompt(row, examples)

    async with semaphore:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
        )

    row["prompt"] = response.choices[0].message.content.strip()
    return row


async def main():
    if not API_KEY:
        raise ValueError("OPENAI_API_KEY is not set")

    client = AsyncOpenAI(api_key=API_KEY)
    examples = "\n".join([f"- {e}" for e in get_example_prompts()])

    semaphore = asyncio.Semaphore(CONCURRENCY)
    tasks = [
        asyncio.create_task(generate_one(client, examples, semaphore)) for _ in range(TOTAL_TASKS)
    ]
    rows = []
    for coro in tqdm(asyncio.as_completed(tasks), total=TOTAL_TASKS, desc="Generating prompts"):
        rows.append(await coro)

    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    asyncio.run(main())
