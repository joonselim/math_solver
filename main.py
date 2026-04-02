import os
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types

# MCP Client Imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()
client = genai.Client()

# ---------------------------------------------------------------------------
# Agent 1: Math Solver (Connects to MCP Server)
# ---------------------------------------------------------------------------
async def run_solver_agent(problem: str) -> str:
    print("\n🤖 [Agent 1: Solver] Initializing MCP connection...")
    
    # Configure MCP Server connection (running the math_server.py locally)
    server_params = StdioServerParameters(
        command="python",
        args=["math_server.py"],
        env=os.environ.copy()
    )

    # Connect to the MCP Server
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as mcp_session:
            await mcp_session.initialize()
            print("✅ [Agent 1: Solver] Connected to MathServer via MCP.")
            
            # For simplicity in this tutorial, we manually define the Gemini tool schema 
            # that matches our MCP tool. (In full ADK, this mapping is automated)
            gemini_calculator_tool = types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="calculate_expression",
                        description="Evaluates a mathematical expression and returns the result.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "expression": types.Schema(type=types.Type.STRING)
                            },
                            required=["expression"]
                        )
                    )
                ]
            )

            system_instruction = """You are an expert Math Solver agent. 
You MUST use the 'calculate_expression' tool for ANY mathematical computation.
Break down the problem step-by-step, use the tool, and then provide the final solution."""

            # Create a chat session with the tool
            chat = client.chats.create(
                model='gemini-2.5-pro',
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=[gemini_calculator_tool],
                    temperature=0.0,
                )
            )

            print("🤖 [Agent 1: Solver] Thinking and solving...")
            response = chat.send_message(problem)

            # --- Agent Event Loop (Handling Tool Calls) ---
            # If the model decides to use the tool, we execute it via MCP and return the result
            while response.function_calls:
                for call in response.function_calls:
                    if call.name == "calculate_expression":
                        expr = call.args.get("expression")
                        print(f"   ⚙️ [Tool Call] Requesting MCP Server to calculate: {expr}")
                        
                        # Call the tool on the MCP server
                        mcp_result = await mcp_session.call_tool("calculate_expression", arguments={"expression": expr})
                        
                        # Parse the text result from the MCP response
                        tool_output = mcp_result.content[0].text if mcp_result.content else "No result"
                        print(f"   ⚙️ [Tool Response] MCP Server returned: {tool_output}")

                        # Send the result back to the model
                        response = chat.send_message(
                            types.Part.from_function_response(
                                name="calculate_expression",
                                response={"result": tool_output}
                            )
                        )
            
            return response.text

# ---------------------------------------------------------------------------
# Agent 2: Math Reviewer (Sequential Execution)
# ---------------------------------------------------------------------------
def run_reviewer_agent(problem: str, solver_solution: str) -> str:
    print("\n🕵️‍♂️ [Agent 2: Reviewer] Reviewing the solver's logic...")
    
    system_instruction = f"""You are a strict Math Reviewer agent.
Review the original problem and the proposed solution.
Check for logical flaws or calculation errors.

If there is an error: Explain the mistake and provide the corrected answer.
If it is correct: State that it is verified and confirm the answer.

[Original Problem]
{problem}

[Proposed Solution]
{solver_solution}
"""

    response = client.models.generate_content(
        model='gemini-2.5-pro',
        contents="Please review the proposed solution.",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.0,
        )
    )
    
    return response.text

# ---------------------------------------------------------------------------
# Pipeline: Sequential Execution Pattern
# ---------------------------------------------------------------------------
async def run_pipeline():
    problem = "A farmer has 14 sheep and 6 cows. He buys 3 more sheep, sells 2 cows, and then multiplies the total number of animals by 15.5. What is the final number?"
    
    print("=" * 70)
    print(f"📝 ORIGINAL PROBLEM:\n{problem}")
    print("=" * 70)
    
    session_state = {
        "problem": problem,
        "solver_output": "",
        "final_reviewed_output": ""
    }
    
    # Step 1: Execute Solver Agent (Async because of MCP)
    session_state["solver_output"] = await run_solver_agent(session_state["problem"])
    print(f"\n✅ [Solver Final Output]\n{session_state['solver_output']}")
    print("-" * 70)
    
    # Step 2: Execute Reviewer Agent (Sync, using data from Step 1)
    session_state["final_reviewed_output"] = run_reviewer_agent(
        problem=session_state["problem"],
        solver_solution=session_state["solver_output"]
    )
    
    print(f"\n🎯 [Reviewer Final Output]\n{session_state['final_reviewed_output']}")
    print("=" * 70)

if __name__ == "__main__":
    # Run the async pipeline
    asyncio.run(run_pipeline())