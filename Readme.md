</br>Working GITHUB MCP Code

- > HTTP way , vs code
-----------------------------------------------------------------
# With MCP adapters - automatic conversion
tools = await load_mcp_tools(session)  # ✅ MCP → LangChain conversion done!

# Without adapters (manual approach):
Manual conversion - you write the wrapper

```mcp_tools = await mcp_client.list_tools()
for t in mcp_tools:
    # Build Pydantic schema
    # Create wrapper function
    # Create StructuredTool
    # Add to tools list
```

---------------------------------------------------------------------------
# What load_mcp_tools does internally:
```
Calls session.list_tools() to get MCP tool definitions
Converts JSON schemas → Pydantic models
Creates async wrapper functions that call session.call_tool()
Wraps in StructuredTool objects
Returns list of LangChain tools ready to use
```

