import asyncio
import uvicorn
import re
from fastapi import FastAPI
from langchain_core.runnables import RunnableLambda, RunnableParallel
from langserve import add_routes

from agents.AI_Investigator import create_investigation_chain, InvestigateRequest
from agents.AI_Validator import create_validation_chain, ValidationInput

# Create a single FastAPI app instance
app = FastAPI(
    title="Combined Cybersecurity Agents API",
    version="1.0",
    description="A single API with endpoints for investigation and validation.",
)

# Global variables to hold the chains
investigation_chain = None
validation_chain = None

# This is an asynchronous startup event handler
@app.on_event("startup")
async def startup_event():
    """
    Initializes the chains asynchronously when the application starts up.
    This runs once, outside of the main event loop.
    """
    global investigation_chain, validation_chain
    # Await the creation of the investigation chain to get the tools
    investigation_chain = await create_investigation_chain()
    # Create the validation chain
    validation_chain = create_validation_chain()

    # Helper: wrap validation to include parsed domain alongside verdict
    def extract_domain(input_obj):
        report_text = getattr(input_obj, "report", None)
        if report_text is None and isinstance(input_obj, dict):
            report_text = input_obj.get("report", "")
        if report_text is None:
            report_text = ""
        pattern = r"\b([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b"
        match = re.search(pattern, report_text, flags=re.IGNORECASE)
        return (report_text, match.group(0).lower() if match else None)

    def normalize_verdict(verdict_text: str) -> str:
        text = (verdict_text or "").strip().lower()
        return "true" if text.startswith("t") else "false"

    wrapped_validation = (
        # Ensure downstream receives a dict {"report": ...}
        RunnableLambda(lambda x: {"report": getattr(x, "report", x.get("report") if isinstance(x, dict) else "")})
        | RunnableParallel(
            verdict=validation_chain,
            report=RunnableLambda(lambda x: x["report"]),
        )
        | RunnableLambda(lambda o: {
            "domain": extract_domain({"report": o["report"]})[1],
            "result": normalize_verdict(o["verdict"].content if hasattr(o["verdict"], "content") else (o["verdict"] if isinstance(o["verdict"], str) else str(o["verdict"]))),
            "report": o["report"],
        })
    )

    # Add routes after the chains have been initialized
    add_routes(
        app,
        investigation_chain.with_types(input_type=InvestigateRequest),
        path="/investigate",
    )
    add_routes(
        app,
        wrapped_validation.with_types(input_type=ValidationInput),
        path="/validate_report",
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5050)
