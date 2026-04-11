from app.agents.trend_agent import trend_agent
from app.agents.compliance_agent import compliance_agent

def run_pipeline():
    trends = trend_agent()

    # Example: just test compliance
    result = compliance_agent(str(trends))

    return {
        "trends": trends,
        "compliance": result
    }
