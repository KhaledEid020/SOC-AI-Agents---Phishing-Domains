import os
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_nvidia_ai_endpoints import ChatNVIDIA

# Define the input schema for the validation endpoint
class ValidationInput(BaseModel):
    """Input for the threat validation endpoint."""
    report: str = Field(
        ...,
        description="The comprehensive security report to validate.",
        example="Threat Summary:\nThe domain youtupe.com has a medium-level threat score of 6.4%, ...",
    )

def create_validation_chain():
    """
    Creates and returns the LCEL chain for the validation agent.
    This is a simpler chain that just uses an LLM to classify a report.
    """
    llm = ChatNVIDIA(
        base_url="http://3.29.243.7:8000/v1",
        model="meta/llama-3.1-8b-instruct",
    )

    # Define the prompt template for the validation task
    validation_prompt = ChatPromptTemplate.from_template(
        "You are a cybersecurity threat validator. Your task is to analyze a security report and determine "
        "if the findings indicate a **true positive** (a real, credible threat) or a **false positive** "
        "(an erroneous or harmless finding). The report you will analyze is provided below."
        "Analyze the details carefully, considering the domain's reputation score, detection ratios, and "
        "related activities. Based on your analysis, respond with only the word 'true' if it is a true positive, "
        "or 'false' if it is a false positive. Do not add any other text, explanation, or punctuation.\n\n"
        "Report to analyze:\n{report}"
    )

    # Build the LCEL chain
    return validation_prompt | llm
