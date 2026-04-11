# ForgeAI

ForgeAI is an AI-powered publishing engine for generating **original, legally safe** KDP products.

## MVP Components

- Trend Agent (safe niche ideation)
- Brand Agent (original brand identity)
- Compliance Agent (hard IP gate)
- PostgreSQL-backed product persistence
- Strict state machine + transition history

## Pipeline State Machine

`idea -> brand -> compliance -> ready`

Only valid forward transitions are allowed via `approve_stage`.

## API

### Create Product
`POST /pipeline/products`

```json
{ "brief": "Mindful productivity journal for remote workers" }
```

### Run Current Stage
`POST /pipeline/{product_id}/run`

### Approve Current Stage
`POST /pipeline/{product_id}/approve`

### Reject Current Stage
`POST /pipeline/{product_id}/reject`

```json
{ "reason": "Needs better uniqueness" }
```

### Regenerate After Failure
`POST /pipeline/{product_id}/regenerate`

Regeneration passes prior failure reasons into agent prompts as guidance.

## Guardrails

- Keyword blacklist (e.g., `ironman`, `avengers`, `naruto`, `batman`)
- Pattern detection (`inspired by`, `like ...`)
- Visual risk heuristics (`armor suit`, `glowing eyes`, etc.)

If guardrails fail, compliance rejects the product and stores failure reasons.

## Run

```bash
pip install -r requirements.txt
./run.sh
```
