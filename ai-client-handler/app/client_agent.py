from agents import Agent, Runner
from app.tools.asana_tool import get_project_status, create_client_task
from services.session_manager import get_history, save_history

client_agent = Agent(
    name="Client Handler",
    model="gpt-4o-mini",  # cost-optimised; swap to gpt-4o for harder queries
    instructions="""
        You are an AI assistant for a software agency.
        Your job is to help clients with:
          - Checking the status of their projects (use get_project_status)
          - Logging new tasks, bugs, or feature requests (use create_client_task)
          - Answering general questions about their work with the agency

        Always check Asana for relevant project information before responding.
        If the client asks to create a task, confirm the details back to them first.
        Be professional, concise, and helpful. Keep replies under 300 characters
        where possible — they are reading on a phone.
    """,
    tools=[get_project_status, create_client_task],
)


async def handle_message(client_id: str, message: str) -> str:
    """Process one inbound message from a client and return the agent reply.

    History flow:
      1. Load prior conversation from Redis (list of SDK-compatible input dicts)
      2. Append the new user message
      3. Run the agent with the full history as input
      4. Persist the updated history (including tool calls) back to Redis
      5. Return the agent's final text output
    """
    history = await get_history(client_id)

    # Append the new user turn
    history.append({"role": "user", "content": message})

    # Run agent — input is the full conversation list
    result = await Runner.run(client_agent, input=history)

    # to_input_list() serialises the full turn (user + tool calls + assistant)
    # in the format Runner.run() expects on the next call
    await save_history(client_id, result.to_input_list())

    return result.final_output
