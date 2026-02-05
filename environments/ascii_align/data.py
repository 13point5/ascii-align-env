DEFAULT_THEMES = [
    {
        "name": "flowcharts",
        "description": "Procedural flowcharts with decisions, loops, and error paths. Clear step labels. Human-like phrasing.",
        "examples": [
            "Draw a flowchart for a password reset flow with an expired-token error path.",
            "Create a flowchart for a checkout process that includes coupon validation and payment failure retry.",
            "Make a flowchart for an incident response runbook: detect -> triage -> mitigate -> postmortem, with an escalation decision.",
        ],
    },
    {
        "name": "architecture",
        "description": "System architecture diagrams: components, data stores, queues, services, arrows indicating data/control flow.",
        "examples": [
            "Draw a web app architecture with client, API, Redis queue, workers, and a Postgres database.",
            "Create an ML inference architecture: request API -> feature store -> model server -> metrics/logging sink.",
            "Draw a CI/CD architecture: repo -> CI runner -> artifact store -> deploy controller -> cluster.",
        ],
    },
    {
        "name": "sequence",
        "description": "Sequence diagrams: participants (lifelines), messages, optional success/failure branches described in text.",
        "examples": [
            "Draw a sequence diagram for login: client -> API -> auth DB -> session store, then back to client.",
            "Create a sequence diagram for file upload: client, API, object storage, virus scanner, metadata DB.",
            "Draw a sequence diagram for data export: user triggers export, job is queued, worker generates file, user downloads.",
        ],
    },
    {
        "name": "state_machines",
        "description": "State machine diagrams: states and transitions with events/conditions.",
        "examples": [
            "Draw a state machine for an order: created -> paid -> shipped -> delivered, with cancel/return branches.",
            "Create a subscription lifecycle state machine: trial, active, past_due, canceled, resumed.",
            "Draw a job state machine: queued, running, succeeded, failed, retried.",
        ],
    },
    {
        "name": "swimlanes",
        "description": "Swimlane diagrams: roles/teams as lanes with steps flowing across lanes.",
        "examples": [
            "Draw a swimlane diagram for feature launch across PM, Engineer, QA, Ops, Marketing.",
            "Create a swimlane diagram for hiring: Candidate, Recruiter, Interview panel, Hiring manager.",
            "Draw a classroom workflow with Teacher vs Student lanes for an in-class activity.",
        ],
    },
    {
        "name": "frameworks",
        "description": "Structured frameworks: 2x2 matrix, timeline, mind map, decision tree, double diamond, journey map.",
        "examples": [
            "Draw a 2x2 impact vs effort matrix with quadrant labels and a few example sticky notes.",
            "Create a timeline with 6 milestones for a product launch from idea to GA.",
            "Draw a mind map for learning Python with 5 branches and 2 sub-branches each.",
        ],
    },
    {
        "name": "syntax_drills",
        "description": "Pure layout/syntax drills: grids, consistent spacing, repeated shapes, simple arrow patterns. Still human-like instructions.",
        "examples": [
            "Draw 12 rectangles in a neat grid labeled A1-C4.",
            "Draw 6 boxes left-to-right with consistent spacing and arrows between them.",
            "Create 4 grouped sections, each containing 3 labeled rectangles.",
        ],
    },
]


def get_default_prompts() -> list[str]:
    return [example for theme in DEFAULT_THEMES for example in theme["examples"]]
