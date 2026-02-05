import asyncio
from langchain_openai import AzureChatOpenAI
from langchain_mcp_adapters.client import load_mcp_tools, load_mcp_resources
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession
from langchain_core.tools import StructuredTool

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

MCP_SERVER_URL = "http://127.0.0.1:8089/mcp"

AZURE_OPENAI_ENDPOINT = ""
AZURE_OPENAI_DEPLOYMENT = "gpt-4.1"
AZURE_OPENAI_API_VERSION = "2024-12-01-preview"
AZURE_OPENAI_API_KEY = ""


async def create_github_agent(session: ClientSession):

    llm = AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        azure_deployment=AZURE_OPENAI_DEPLOYMENT,
        api_version=AZURE_OPENAI_API_VERSION,
        temperature=0
    )

    print("🔧 Loading MCP tools and resources...")
    
    # Load tools
    tools = await load_mcp_tools(session)
    print(f"\n📦 MCP TOOLS ({len(tools)}):")
    for t in tools:
        print(f"   🔧 {t.name}: {t.description}")
    
    # Load and convert resources
    resource_blobs = await load_mcp_resources(session)
    print(f"\n📚 MCP RESOURCES ({len(resource_blobs)}):")
    
    for blob in resource_blobs:
        uri = blob.metadata.get('uri') if hasattr(blob, 'metadata') else 'unknown'
        print(f"   📄 {uri}")
        
        # Create closure to capture blob data
        def make_resource_tool(resource_data, resource_uri):
            def get_resource():
                """Get resource data"""
                print(f"   🔍 [RESOURCE CALLED] {resource_uri}")
                return str(resource_data)
            return get_resource
        
        tool_name = f"get_{str(uri)}".replace('://', '_').replace('/', '_')
        resource_tool = StructuredTool.from_function(
            func=make_resource_tool(blob.data, uri),
            name=tool_name,
            description=f"Get data from resource {uri}"
        )
        tools.append(resource_tool)
        print(f"      → Converted to tool: {tool_name}")
    
    print(f"\n✅ Total tools available: {len(tools)}")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful GitHub assistant. Use tools and resources to answer questions accurately and concisely."),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}")
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5
    )


async def main():
    print("=" * 60)
    print("🚀 GitHub MCP Agent")
    print("=" * 60)
    print(f"\n🔌 Connecting to MCP server: {MCP_SERVER_URL}")

    async with streamablehttp_client(MCP_SERVER_URL) as (reader, writer, _):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            print("✅ Connected!")

            agent = await create_github_agent(session)

            print("\n" + "=" * 60)
            print("💬 Ask questions about your GitHub repository")
            print("   Type 'exit' or 'quit' to stop")
            print("=" * 60)

            while True:
                user_input = input("\n🤔 Your question: ").strip()

                if user_input.lower() in ["exit", "quit"]:
                    print("\n👋 Goodbye!")
                    break

                if not user_input:
                    continue

                print("\n" + "-" * 60)
                try:
                    result = await agent.ainvoke({"input": user_input})
                    print("\n" + "=" * 60)
                    print("🧠 RESPONSE:")
                    print(result["output"])
                    print("=" * 60)
                except Exception as e:
                    print(f"\n❌ Error: {e}")
                    import traceback
                    traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
