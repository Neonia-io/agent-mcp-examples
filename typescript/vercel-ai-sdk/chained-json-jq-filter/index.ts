import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { generateText, tool as aiTool, jsonSchema, stepCountIs } from 'ai';
import { createOpenRouter } from '@openrouter/ai-sdk-provider';
import * as dotenv from 'dotenv';

dotenv.config();

async function main() {
    console.log("[System] Connecting to Neonia MCP Gateway...");

    // 1. Setup MCP Client
    const neoniaApiKey = process.env.NEONIA_API_KEY;
    const headers = neoniaApiKey ? { "Authorization": `Bearer ${neoniaApiKey}` } : undefined;
    const transport = new StreamableHTTPClientTransport(new URL("https://mcp.neonia.io/mcp?tools=neo_web_json_fetch,neo_data_jq_filter"), {
        requestInit: headers ? { headers } : undefined
    });
    const client = new Client({
        name: "01-chained-json-jq-filter",
        version: "1.0.0"
    }, {
        capabilities: {}
    });

    await client.connect(transport);
    console.log("[System] Connected successfully to Neonia MCP.");

    // 2. Fetch and filter tools
    const toolsList = await client.listTools();
    const allowedTools = ["neo_web_json_fetch", "neo_data_jq_filter"];
    const filteredMcpTools = toolsList.tools.filter(t => allowedTools.includes(t.name));

    const tools: Record<string, any> = {};
    for (const mcpTool of filteredMcpTools) {
        tools[mcpTool.name] = aiTool({
            description: mcpTool.description || "",
            parameters: jsonSchema(JSON.parse(JSON.stringify(mcpTool.inputSchema))),
            execute: async (args: any) => {
                console.log(`\n[Autonomy] Agent calls ${mcpTool.name} with arguments:`, JSON.stringify(args));
                try {
                    const result = await client.callTool({
                        name: mcpTool.name,
                        arguments: args
                    });
                    if (result.isError) {
                        console.error(`[Error] Tool returned error:`, result.content);
                        return `Error: ${JSON.stringify(result.content as any)}`;
                    }
                    
                    // Extract text content directly as a string to avoid OpenRouter parsing errors
                    const content = result.content as any[];
                    const textParts = content
                        .filter(c => c.type === 'text')
                        .map(c => c.text);
                    
                    return textParts.join('\n');
                } catch (error) {
                    console.error(`[Error] Execution error in ${mcpTool.name}:`, error);
                    return `Error: ${String(error)}`;
                }
            }
        } as any);
    }

    console.log(`[System] Agent equipped with ${Object.keys(tools).length} foundational tools.`);
    console.log("[System] Starting task...\n");

    // 3. Run Agent
    const targetUrl = "https://dummyjson.com/posts";
    
    const openrouter = createOpenRouter({
        apiKey: process.env.OPENROUTER_API_KEY,
    });
    
    const result = await generateText({
        model: openrouter('anthropic/claude-3.7-sonnet'),
        tools: tools,
        stopWhen: stepCountIs(5),
        system: "You are an autonomous agent equipped with Neonia's data processing tools.\n" +
                "## Usage Guidelines\n" +
                "1. When asked to process JSON from a URL, ALWAYS use `neo_web_json_fetch` first. It will securely store the file and return a `resource_uri` and a TypeScript schema of the data.\n" +
                "2. Once you have the `resource_uri` and the schema, use `neo_data_jq_filter` to extract exactly what you need. Pass the `resource_uri` to the `resource_uri` parameter, and formulate a mathematically precise `jq_query` based on the schema.\n" +
                "3. Write correct JQ queries. If the JSON has a wrapper object like `.posts`, use appropriate mapping. Example: `.posts[0:10] | map({title: .title, body: .body})`.\n" +
                "4. Self-Correction: If a tool returns an error, evaluate your parameters, fix them, and try again.",
        prompt: `Fetch the JSON from ${targetUrl}, then use the jq filter to extract the title and body of the first 10 posts. Finally, provide a brief summary of the posts.`,
        onStepFinish: (step) => {
            const toolCalls = step.toolCalls.map(t => t.toolName).join(", ");
            if (toolCalls) {
                console.log(`[Autonomy] Agent called tools: ${toolCalls}`);
            }
            if (toolCalls.includes('neo_web_json_fetch')) {
                console.log(`[Autonomy] Fetched JSON successfully and received pointer!`);
            }
            if (toolCalls.includes('neo_data_jq_filter')) {
                console.log(`[Autonomy] Filtered JSON successfully using JQ and pointer!`);
            }
        }
    });

    console.log("\n[Result]:");
    console.log(result.text);

    // Clean up
    transport.close();
    process.exit(0);
}

main().catch(console.error);
