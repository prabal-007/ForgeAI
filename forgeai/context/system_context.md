# ForgeAI System Context

ForgeAI is an AI-powered publishing system designed to create legally safe, original KDP products (journals, notebooks, planners).

## Core Principle
This system MUST NEVER generate or allow:
- Copyrighted characters
- Trademarked names
- Franchise references
- Derivative designs

## Pipeline
Each product flows through:

IDEA → VALIDATION → BRAND → DESIGN → CONTENT → COMPLIANCE → READY

## Architecture
- Backend: FastAPI
- Agents: modular Python functions using LLMs
- Orchestration: state-based pipeline
- DB: PostgreSQL (future)
- Vector DB: optional

## Agent Rules
- Always return structured JSON
- Never hallucinate brand safety
- Compliance agent has final authority (can kill pipeline)

## Compliance Rules
- Reject anything resembling known IP
- Reject keywords like: ironman, avengers, naruto, batman, etc.
- Reject “inspired by” patterns

## Development Style
- Keep functions small and testable
- Prefer explicit over magic
- All agent outputs must be validated

## Goal
Build a scalable system that generates original IP safely and repeatedly.
