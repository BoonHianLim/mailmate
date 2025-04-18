import logging
import os
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import ToolMessage, BaseMessage
from langchain.prompts import ChatPromptTemplate

from tools.search_emails import get_search_emails_tool
from tools.inbox_summary import get_generate_inbox_summary_tool

# Load environment variables
logger: logging.Logger = logging.getLogger("uvicorn.error")


def call_tool(user_id: str, query: str, system: str) -> str:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    """
    Call the appropriate tool based on the query.
    """
    # Initialize the Gemini LLM (using ChatGoogleGenerativeAI)
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-001",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        google_api_key=GOOGLE_API_KEY,
    )

    # Import your pre-built tools.
    # Make sure these functions (search_emails_tool and generate_inbox_summary) are defined and available.
    # For example, they could be imported from a module named "my_tools".

    # Define the list of available tools.
    generate_inbox_summary = get_generate_inbox_summary_tool(user_id)
    search_emails_tool = get_search_emails_tool(user_id)
    tools = [search_emails_tool, generate_inbox_summary]

    # Define a prompt that instructs the agent how to choose between tools.
    # The prompt provides high-level instructions:
    # - Use search_emails_tool if the query looks like a targeted email search.
    # - Use generate_inbox_summary if the query asks for a general summary of the inbox.
    llm_with_tools = llm.bind_tools(tools)
    function_call_response = llm_with_tools.invoke(query)

    results: list[ToolMessage] = []
    tool_calls = getattr(function_call_response, "tool_calls", None)
    if len(tool_calls) == 0:
        human_response = natural_language_response(system, query)
        return human_response.content
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        # Find the tool by name
        tool_func = next((t for t in tools if t.name == tool_name), None)
        if tool_func is None:
            raise Exception(f"Tool '{tool_name}' not found.")

        # Run the tool
        output = tool_func.invoke(tool_args)
        results.append(ToolMessage(
            tool_call_id=tool_call["id"], content=output))

    print("Invoke completed successfully.")

    tool_output = results[0].content
    tool_query = f"""The user asked: {query}
    
    After processing their requests, the tool returned the following:\n\n{tool_output}

    Return response that suits your personality, tone, and style.
    """
    logger.info(f"Tool query: {tool_query}")
    human_response = natural_language_response(system, tool_query)

    return human_response.content


def natural_language_response(system: str, query: str) -> BaseMessage:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    llm_for_output = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-001",
        temperature=0.7,
        google_api_key=GOOGLE_API_KEY,
    )

    post_tool_prompt = ChatPromptTemplate.from_messages(
        [("system", system), ("human", query)]
    )
    chain = post_tool_prompt | llm_for_output
    human_response = chain.invoke({})
    logger.info(f"Result summary: {human_response}")
    return human_response
