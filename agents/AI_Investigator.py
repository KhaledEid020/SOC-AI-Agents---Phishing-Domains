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
    MCP_API_KEY = os.environ.get("MCP_API_KEY", "xxxxxx")

    mcp_client = MultiServerMCPClient(
        {
            "mcp_server": {
                "transport": "streamable_http",
                "url": "http://xxxxx:4444/servers/xxxxxx/mcp",
                "headers": {"Authorization": f"Bearer {MCP_API_KEY}"},
            }
        }
    )
    # The MCP client needs to be awaited to get the tools
    tools = await mcp_client.get_tools()

    llm = ChatNVIDIA(
        base_url="http://xxxxx:8000/v1",
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
