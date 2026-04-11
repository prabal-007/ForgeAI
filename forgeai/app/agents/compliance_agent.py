from app.services.llm_service import run_prompt

BLACKLIST = ["ironman", "avengers", "naruto", "batman"]

def compliance_agent(text: str):
    for word in BLACKLIST:
        if word in text.lower():
            return {
                "risk": "high",
                "issues": [f"blacklisted keyword: {word}"],
                "decision": "fail"
            }

    with open("prompts/compliance.txt") as f:
        prompt = f.read() + f"\n\nContent:\n{text}"

    return run_prompt(prompt)
