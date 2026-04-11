from app.services.llm_service import run_prompt

def trend_agent():
    with open("prompts/trend.txt") as f:
        prompt = f.read()

    return run_prompt(prompt)
