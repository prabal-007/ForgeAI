# ForgeAI

ForgeAI is an AI-powered publishing engine for generating **original, legally safe** KDP products.

## MVP Components

- Trend Agent (safe niche ideation)
- Brand Agent (original brand identity)
- Compliance Agent (hard IP gate)
- Stateful orchestrator (IDEA → BRAND → COMPLIANCE → READY in MVP)
- FastAPI endpoint to run pipeline with human approvals

## API

### Run Pipeline

`POST /pipeline/run`

Example payload:

```json
{
  "brief": "Mindful productivity journal for remote workers",
  "approve_idea": true,
  "approve_brand": true
}
```

## Guardrails

- Keyword blacklist (e.g., `ironman`, `avengers`, `naruto`, `batman`)
- Pattern detection (`inspired by`, `like ...`)
- Visual risk heuristics (`armor suit`, `glowing eyes`, etc.)

If guardrails fail, the pipeline is rejected before final compliance scoring.

## Run

```bash
pip install -r requirements.txt
./run.sh
```
