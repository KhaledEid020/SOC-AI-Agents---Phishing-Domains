import asyncio
import os
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

# Input schema for the investigation endpoint
class InvestigateRequest(BaseModel):
    """Input for the investigation endpoint."""
    target: str = Field(
        ...,
        description="The domain to investigate.",
        example="google.com",
    )

async def create_investigation_chain():
    """
    Creates and initializes the ReAct agent for security investigation.
    This function is async because it needs to get tools from the client.
    """
    MCP_API_KEY = os.environ.get("MCP_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImFkbWluQGV4YW1wbGUuY29tIiwiaWF0IjoxNzYxNzY2Njc4LCJpc3MiOiJtY3BnYXRld2F5IiwiYXVkIjoibWNwZ2F0ZXdheS1hcGkiLCJzdWIiOiJhZG1pbkBleGFtcGxlLmNvbSIsImV4cCI6MTc2MjM3MTQ3OH0.5PQwXmQ7cvti923VOnBuB4gbSg0Jym2IKKFjG3Cw-L0")

    mcp_client = MultiServerMCPClient(
        {
            "mcp_server": {
                "transport": "streamable_http",
                "url": "http://3.28.242.189:4444/servers/55b450a0ac8b4cfa9f620eadda52c05b/mcp",
                "headers": {"Authorization": f"Bearer {MCP_API_KEY}"},
            }
        }
    )
    # The MCP client needs to be awaited to get the tools
    tools = await mcp_client.get_tools()

    llm = ChatNVIDIA(
        base_url="http://3.29.243.7:8000/v1",
        model="meta/llama-3.1-8b-instruct",
    )
    # Create the ReAct agent executor with the LLM and tools
    agent_executor = create_react_agent(llm, tools)

    # Define the prompt template for the investigation
    investigation_prompt = ChatPromptTemplate.from_template(
        "You are a Senior Cybersecurity Analyst; use the get domain report tool to investigate {target}, "
        "then provide a comprehensive security investigation report including how many the domain has been flagged as malicious by security vendors and what are these vednors,"
        "risk assessment, related activities, historical reputation, and recommended mitigations."
    )

    # Build the complete LCEL chain for the investigation agent
    return (
        investigation_prompt
        | RunnableLambda(lambda x: {"messages": [{"role": "user", "content": x.to_string()}]})
        | agent_executor
    )
