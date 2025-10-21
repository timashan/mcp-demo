from dotenv import load_dotenv
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import List
import asyncio
import nest_asyncio
import json

nest_asyncio.apply()

load_dotenv()


class MCP_ChatBot:
    def __init__(self):
        # Initialize session and client objects
        self.session: ClientSession = None
        self.client = OpenAI()
        self.available_tools: List[dict] = []

    async def process_query(self, query):
        messages = [{"role": "user", "content": query}]
        response = self.client.chat.completions.create(
            model="gpt-4o",
            tools=self.available_tools,  # tools exposed to the LLM
            messages=messages,
        )

        process_query = True
        while process_query:
            message = response.choices[0].message

            # Check if there are tool calls
            if message.tool_calls:
                # Add assistant message to conversation
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": message.tool_calls,
                    }
                )

                # Process each tool call
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    tool_id = tool_call.id

                    print(f"Calling tool {tool_name} with args {tool_args}")

                    # Call tool through the MCP client session
                    result = await self.session.call_tool(
                        tool_name, arguments=tool_args
                    )

                    # Extract text content from MCP result
                    tool_result_content = ""
                    if isinstance(result.content, list):
                        for item in result.content:
                            if hasattr(item, "text"):
                                tool_result_content += item.text
                            elif isinstance(item, dict) and "text" in item:
                                tool_result_content += item["text"]
                    else:
                        tool_result_content = str(result.content)

                    # Add tool result to messages
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": tool_result_content,
                        }
                    )

                # Get next response from model
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    tools=self.available_tools,
                    messages=messages,
                )
            else:
                # No tool calls, print final response and exit loop
                if message.content:
                    print(message.content)
                process_query = False

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Chatbot Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                await self.process_query(query)
                print("\n")

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def connect_to_server_and_run(self):
        # Create server parameters for stdio connection
        server_params = StdioServerParameters(
            command="uv",  # Executable
            args=["run", "server.py"],  # Optional command line arguments
            env=None,  # Optional environment variables
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session
                # Initialize the connection
                await session.initialize()

                # List available tools
                response = await session.list_tools()

                tools = response.tools
                print(
                    "\nConnected to server with tools:", [tool.name for tool in tools]
                )

                # Convert MCP tools to OpenAI function calling format
                self.available_tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema,
                        },
                    }
                    for tool in response.tools
                ]

                await self.chat_loop()


async def main():
    chatbot = MCP_ChatBot()
    await chatbot.connect_to_server_and_run()


if __name__ == "__main__":
    asyncio.run(main())
