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
    const transport = new StreamableHTTPClientTransport(new URL("https://mcp.neonia.io/mcp?tools=neo_data_jq_filter"), {
        requestInit: headers ? { headers } : undefined
    });
    const client = new Client({
        name: "01-zero-bloat-jq-filter",
        version: "1.0.0"
    }, {
        capabilities: {}
    });

    await client.connect(transport);
    console.log("[System] Connected successfully to Neonia MCP.");

    // 2. Fetch and filter tools
    const toolsList = await client.listTools();
    const allowedTools = ["neo_data_jq_filter"];
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
    const targetUrl = "https://dummyjson.com/carts";
    
    const openrouter = createOpenRouter({
        apiKey: process.env.OPENROUTER_API_KEY,
    });
    
    const result = await generateText({
        model: openrouter('anthropic/claude-3.7-sonnet'),
        tools: tools,
        stopWhen: stepCountIs(5),
        system: "You are an autonomous agent equipped with the neo_data_jq_filter tool.\n" +
                "CRITICAL SYSTEM TOOL: This is a core data manipulation capability. ALWAYS use this to extract specific fields or filter arrays from large JSON files instead of trying to parse them entirely inside your context window or hallucinating data structures.\n" +
                "## Usage Guidelines\n" +
                "1. Prefer data_url for large files: If you need to read JSON from a URL (e.g. an API endpoint), pass the URL to data_url and the tool will fetch and process it natively in its memory, completely bypassing your token limits.\n" +
                "2. Use raw_json for existing data: If you already have the data in a variable or context and just need to query it, pass it as a string to raw_json.\n" +
                "3. Write correct JQ queries: Pass the filter to jq_query. Examples: .[] | .id, .users[0].name, map(select(.active == true)).\n" +
                "4. Self-Correction: If the tool returns 'Invalid JQ syntax. Please correct your query.', evaluate your query string, fix the syntax error, and call the tool again.",
        prompt: `Find the total discountedTotal for all carts at this URL: ${targetUrl}`,
        onStepFinish: (step) => {
            const toolCalls = step.toolCalls.map(t => t.toolName).join(", ");
            if (toolCalls) {
                console.log(`[Autonomy] Agent called tools: ${toolCalls}`);
            }
            if (toolCalls.includes('neo_data_jq_filter')) {
                console.log(`[Autonomy] Saved ~50,000 tokens by using remote JQ filter!`);
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
