#WE HAVE NOT USED LANGCHAIN ADAPTERS FOR MCP -> OLDER WAY->SO WE NEED TO CONVERT MCP TOOL TO LANCHAIN TOOL


import asyncio
import json
from langchain_core.tools import StructuredTool
from langchain_openai import AzureChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from pydantic import Field, create_model

# ==========================================================
# Configuration
# ==========================================================
MCP_SERVER_URL = "http://127.0.0.1:8089/mcp"

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = ""
AZURE_OPENAI_API_KEY = "???????????"
AZURE_OPENAI_DEPLOYMENT = "gpt-4.1"
AZURE_OPENAI_API_VERSION = "2024-12-01-preview"

# ==========================================================
# Dynamic Tool Creation from MCP
# ==========================================================

def create_langchain_tools_from_mcp(mcp_client: Client):
    """Dynamically create LangChain tools from MCP server"""
    
    langchain_tools = []
    
    # This will be populated inside the async context
    return langchain_tools


async def fetch_mcp_tools_old(mcp_client: Client):
    """Fetch tools from MCP server (must be called inside async with)"""
    
    from pydantic import BaseModel, Field, create_model
    from typing import Type
    
    langchain_tools = []
    
    # Get the current event loop
    loop = asyncio.get_event_loop()
    
    # Get MCP tools
    mcp_tools = await mcp_client.list_tools()
    print(f"\n📋 Found {len(mcp_tools)} MCP tools")
    
    for mcp_tool in mcp_tools:
        tool_name = mcp_tool.name
        tool_description = mcp_tool.description or f"MCP tool: {tool_name}"
        input_schema = mcp_tool.inputSchema if hasattr(mcp_tool, 'inputSchema') else {}
        
        print(f"   ✓ {tool_name}")
        print(f"     Schema: {input_schema}")  # Debug output
        
        # Create Pydantic model from input schema
        if input_schema and 'properties' in input_schema:
            fields = {}
            properties = input_schema.get('properties', {})
            required = input_schema.get('required', [])
            
            for prop_name, prop_schema in properties.items():
                prop_type = str  # Default to string
                prop_description = prop_schema.get('description', '')
                
                # Map JSON schema types to Python types
                json_type = prop_schema.get('type', 'string')
                if json_type == 'integer':
                    prop_type = int
                elif json_type == 'number':
                    prop_type = float
                elif json_type == 'boolean':
                    prop_type = bool
                
                # Add field with description
                if prop_name in required:
                    fields[prop_name] = (prop_type, Field(..., description=prop_description))
                else:
                    fields[prop_name] = (prop_type, Field(None, description=prop_description))
            
            # Create dynamic Pydantic model
            ArgsSchema = create_model(f"{tool_name}Args", **fields)
        else:
            ArgsSchema = None
        
        # Create a wrapper function for this tool
        def make_tool_func(name, client):
            def tool_func(**kwargs) -> str:
                print(f"[DEBUG] Calling tool '{name}' with kwargs: {kwargs}")
                
                try:
                    # Use asyncio to run coroutine in existing loop
                    coro = client.call_tool(name, kwargs)
                    # Check if we're in an event loop
                    try:
                        loop = asyncio.get_running_loop()
                        # We're in a loop, create a task
                        import nest_asyncio
                        nest_asyncio.apply()
                        result = asyncio.run(coro)
                    except RuntimeError:
                        # No loop running, safe to use asyncio.run
                        result = asyncio.run(coro)
                    
                    # Extract text content from result
                    if hasattr(result, 'content') and result.content:
                        content_obj = result.content[0]
                        if hasattr(content_obj, 'text'):
                            return content_obj.text
                        elif hasattr(content_obj, 'json'):
                            return json.dumps(content_obj.json, indent=2)
                    return str(result)
                    
                except Exception as e:
                    # Return error as string so agent can handle it
                    error_msg = str(e)
                    print(f"[ERROR] Tool '{name}' failed: {error_msg}")
                    
                    # Provide helpful context based on the error
                    if "404" in error_msg and "pulls" in error_msg:
                        return f"Error: Issue #{kwargs.get('number', 'unknown')} is not a pull request. Try using list_all_issues to check if it's an issue instead."
                    elif "404" in error_msg:
                        return f"Error: Resource not found. The item #{kwargs.get('number', 'unknown')} may not exist."
                    else:
                        return f"Error calling tool: {error_msg}"
            return tool_func
        
        # Create LangChain StructuredTool with proper schema
        lc_tool = StructuredTool.from_function(
            func=make_tool_func(tool_name, mcp_client),
            name=tool_name,
            description=tool_description,
            args_schema=ArgsSchema
        )
        
        langchain_tools.append(lc_tool)
    
    # Get MCP resources
    mcp_resources = await mcp_client.list_resources()
    print(f"\n📦 Found {len(mcp_resources)} MCP resources")
    
    for resource in mcp_resources:
        uri = resource.uri
        name = resource.name or uri.replace("://", "_").replace("/", "_")
        description = resource.description or f"Access resource: {uri}"
        
        print(f"   ✓ {name} ({uri})")
        
        # Create a wrapper function for this resource
        def make_resource_func(resource_uri, client):
            def resource_func() -> str:
                coro = client.read_resource(resource_uri)
                try:
                    loop = asyncio.get_running_loop()
                    import nest_asyncio
                    nest_asyncio.apply()
                    result = asyncio.run(coro)
                except RuntimeError:
                    result = asyncio.run(coro)
                
                if hasattr(result, 'contents') and result.contents:
                    content_obj = result.contents[0]
                    if hasattr(content_obj, 'text'):
                        return content_obj.text
                    elif hasattr(content_obj, 'json'):
                        return json.dumps(content_obj.json, indent=2)
                return str(result)
            return resource_func
        
        # Create LangChain tool for resource
        lc_tool = StructuredTool.from_function(
            func=make_resource_func(uri, mcp_client),
            name=f"get_{name}",
            description=description
        )
        
        langchain_tools.append(lc_tool)
    
    return langchain_tools

async def fetch_mcp_tools(mcp_client: Client):
    tools = []

    mcp_tools = await mcp_client.list_tools()
    print(f"Loaded {len(mcp_tools)} MCP tools")
    
    for t in mcp_tools:
        schema = getattr(t, "inputSchema", {}) or {}
        ArgsSchema = None
        if "properties" in schema:
            fields = {}
            required = set(schema.get("required", []))
            type_map = {"string": str, "integer": int, "number": float, "boolean": bool}
            for name, spec in schema["properties"].items():
                py_t = type_map.get(spec.get("type", "string"), str)
                desc = spec.get("description", "")
                default = ... if name in required else None
                fields[name] = (py_t, Field(default, description=desc))
            ArgsSchema = create_model(f"{t.name}Args", **fields)

        # Create closure to capture tool name
        # Your wrapper converts LangChain call → MCP HTTP call
        def make_wrapper(tool_name):
            async def _runner(**kwargs):
                try:
                    # This makes HTTP call to MCP server
                    r = await mcp_client.call_tool(tool_name, kwargs)
                    if getattr(r, "content", None):
                        c = r.content[0]
                        if hasattr(c, "text"): 
                            return c.text
                        if hasattr(c, "json"): 
                            return json.dumps(c.json, indent=2)
                    return str(r)
                except Exception as e:
                    msg = str(e)
                    if "404" in msg and "pulls" in msg:
                        return f"Error: #{kwargs.get('number','?')} is not a pull request."
                    if "404" in msg:
                        return f"Error: Not found #{kwargs.get('number','?')}."
                    return f"Error: {msg}"
            
            return _runner  # Return async function directly
        
        tools.append(
            # Now LangChain can call it like a normal function
            StructuredTool.from_function(
                coroutine=make_wrapper(t.name),  # Use coroutine= for async
                name=t.name,
                description=t.description or f"MCP tool {t.name}",
                args_schema=ArgsSchema
            )
        )

    resources = await mcp_client.list_resources()
    print(f"Loaded {len(resources)} MCP resources")
    
    for r in resources:
        uri = r.uri
        label = r.name or uri.replace("://", "_").replace("/", "_")
# Your wrapper converts LangChain call → MCP HTTP call
        def make_resource_wrapper(resource_uri):
            async def _read():
                res = await mcp_client.read_resource(resource_uri)
                if getattr(res, "contents", None):
                    c = res.contents[0]
                    if hasattr(c, "text"): 
                        return c.text
                    if hasattr(c, "json"): 
                        return json.dumps(c.json, indent=2)
                return str(res)
            
            return _read  # Return async function directly

        tools.append(
            StructuredTool.from_function(
                coroutine=make_resource_wrapper(uri),  # Use coroutine= for async
                name=f"get_{label}",
                description=r.description or f"Resource {uri}"
            )
        )
    
    return tools
# ==========================================================
# Create LangChain Agent with Azure OpenAI
# ==========================================================

async def create_github_agent(mcp_client: Client):
    """Create a LangChain agent with Azure OpenAI and dynamically loaded MCP tools"""
    
    # Initialize Azure OpenAI LLM
    llm = AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        azure_deployment=AZURE_OPENAI_DEPLOYMENT,
        api_version=AZURE_OPENAI_API_VERSION,
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )
    
    # Get tools dynamically from MCP
    tools = await fetch_mcp_tools(mcp_client)
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful GitHub assistant connected to a GitHub repository via MCP.
        
You have access to various tools and resources to help users interact with their repository.

Important Guidelines:
- Use get_pr_details for PULL REQUESTS only - it returns PR metadata but NOT review comments
- Use list_all_issues to find and get details about ISSUES
- NEVER call the same tool with the same parameters twice - you already have that information
- If a tool returns an error, try an alternative approach
- Issues and Pull Requests have different IDs - an issue #89 is NOT the same as PR #89
- Review comments are NOT included in get_pr_details - if user asks for review comments, explain that this functionality requires GitHub API's review comments endpoint which is not currently available

Think step by step:
1. Check what information you already have from previous tool calls
2. Only call a tool if you need NEW information
3. If the data isn't available, clearly explain what's missing

Be concise, clear, and helpful in your responses."""),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}")
    ])
    
    # Create agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    # Create agent executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5
    )
    
    return agent_executor


# ==========================================================
# Main Execution
# ==========================================================

async def main():
    print("=" * 60)
    print("GitHub MCP Agent with Azure OpenAI + LangChain")
    print("=" * 60)
    
    # Initialize MCP client with StreamableHttpTransport
    transport = StreamableHttpTransport(url=MCP_SERVER_URL)
    mcp_client = Client(transport)
    
    async with mcp_client:
        # Test connection
        try:
            print("\n🔌 Connecting to MCP server...")
            await mcp_client.ping()
            print("✓ Connected successfully!")
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Create agent with Azure OpenAI
        print("\n🤖 Creating agent with Azure OpenAI...")
        agent = await create_github_agent(mcp_client)
        print("✓ Agent ready!")
        
        # Show available tools
        print("\n📋 Available tools for the agent:")
        tools = await fetch_mcp_tools(mcp_client)
        for tool in tools:
            print(f"   - {tool.name}: {tool.description}")
        
        print("\n" + "=" * 60)
        print("You can now ask questions about your GitHub repository.")
        print("Type 'quit' or 'exit' to stop.")
        print("=" * 60)
        
        # Interactive loop
        while True:
            try:
                user_input = input("\n🤔 Your question: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                print("\n" + "-" * 60)
                
                # Run agent
                response = await agent.ainvoke({"input": user_input})  # Use ainvoke instead of invoke
                
                print("\n" + "=" * 60)
                print("📝 Answer:")
                print(response.get("output", "No response"))
                print("=" * 60)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
