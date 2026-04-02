from mcp.server.fastmcp import FastMCP

# 1. Initialize the FastMCP Server
mcp = FastMCP("MathServer")

# 2. Define the tool using the decorator
@mcp.tool()
def calculate_expression(expression: str) -> str:
    """
    Evaluates a mathematical expression and returns the result.
    Use this tool for ANY mathematical calculation.
    
    Args:
        expression: A valid Python mathematical expression (e.g., '2 * (3 + 4)').
    """
    try:
        # Note: eval() is used here for simplicity. 
        # In a production environment, use a safer math evaluator (e.g., ast.literal_eval or numexpr)
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error computing expression: {e}"

if __name__ == "__main__":
    # Run the server using stdio transport (standard for local MCP tools)
    print("🚀 Math MCP Server is starting...")
    mcp.run()