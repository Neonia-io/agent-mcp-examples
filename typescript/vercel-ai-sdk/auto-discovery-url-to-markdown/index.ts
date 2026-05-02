import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { generateText, tool as aiTool, stepCountIs, jsonSchema } from 'ai';
import { createOpenRouter } from '@openrouter/ai-sdk-provider';
import * as dotenv from 'dotenv';

dotenv.config();

async function main() {
    console.log("[System] Connecting to Neonia MCP Gateway with Auto-Pilot Tools...");

    // 1. Setup MCP Client
    const neoniaApiKey = process.env.NEONIA_API_KEY;
    const headers = neoniaApiKey ? { "Authorization": `Bearer ${neoniaApiKey}` } : undefined;

    // Connect with explicit ?tools= query string to avoid 404 from Gateway
    const transport = new StreamableHTTPClientTransport(new URL("https://mcp.neonia.io/mcp?tools=neo_sys_tool_discovery,neo_sys_tool_execute"), {
        requestInit: headers ? { headers } : undefined
    });

    const client = new Client({
        name: "mcp-auto-discovery-agent",
        version: "1.0.0"
    }, {
        capabilities: {}
    });

    await client.connect(transport);
    console.log("[System] Connected successfully to Neonia MCP.");

    // 2. Fetch and filter tools
    const toolsList = await client.listTools();
    console.log(`[System] Initial Agent tools cached: [${toolsList.tools.map(t => t.name).join(", ")}]\n`);

    const tools = {
        neo_sys_tool_discovery: aiTool({
            description: "Search the Neonia Gateway for tools, or request new ones if they don't exist.",
            parameters: jsonSchema<{ query: string }>({
                type: "object",
                properties: {
                    query: { type: "string", description: "Search query to find the tool" }
                },
                required: ["query"],
                additionalProperties: false
            }),
            execute: async ({ query }: { query: string }) => {
                if (!query) return "Error: 'query' parameter is required. Please provide a search query.";
                console.log(`\n[Autonomy] Agent searches for tool: ${query}`);
                try {
                    const result = await client.callTool({
                        name: "neo_sys_tool_discovery",
                        arguments: { query }
                    });
                    if (result.isError) return `Error: ${JSON.stringify(result.content)}`;
                    const content = result.content as Array<{ type: string; text?: string }>;
                    return content.filter(c => c.type === 'text').map(c => c.text || '').join('\n');
                } catch (error) {
                    return `Error: ${String(error)}`;
                }
            }
        }),
        neo_sys_tool_execute: aiTool({
            description: "CRITICAL: The Auto-Pilot engine. Allows your AI to dynamically execute tools on the fly. You MUST pass 'target_tool' as the tool name and 'payload' as the EXACT JSON arguments object.",
            parameters: jsonSchema<{ target_tool: string, payload: Record<string, unknown> }>({
                type: "object",
                properties: {
                    target_tool: { type: "string", description: "The name of the tool to execute" },
                    payload: { type: "object", description: "The JSON payload arguments required by the target tool", additionalProperties: true }
                },
                required: ["target_tool", "payload"],
                additionalProperties: false
            }),
            execute: async ({ target_tool, payload }: { target_tool: string, payload: Record<string, unknown> }) => {
                if (!target_tool || !payload) return "Error: 'target_tool' and 'payload' parameters are required.";
                console.log(`\n[Autonomy] Agent executes ${target_tool} with payload:`, JSON.stringify(payload));
                try {
                    const result = await client.callTool({
                        name: "neo_sys_tool_execute",
                        arguments: { target_tool, payload }
                    });
                    if (result.isError) return `Error: ${JSON.stringify(result.content)}`;
                    const content = result.content as Array<{ type: string; text?: string }>;
                    return content.filter(c => c.type === 'text').map(c => c.text || '').join('\n');
                } catch (error) {
                    return `Error: ${String(error)}`;
                }
            }
        })
    };

    console.log("[System] Starting task...\n");

    // 3. Run Agent
    const targetUrl = "https://neonia.io";

    const openrouter = createOpenRouter({
        apiKey: process.env.OPENROUTER_API_KEY,
    });

    const result = await generateText({
        model: openrouter('google/gemini-3-flash-preview'),
        tools: tools,
        stopWhen: stepCountIs(5),
        system: "You are an autonomous agent equipped with Neonia's auto-pilot capabilities. " +
            "If you need a tool you do not have, use `neo_sys_tool_discovery` to find it. " +
            "Once found, explicitly run it using `neo_sys_tool_execute` without asking the user. " +
            "CRITICAL: When using neo_sys_tool_execute, you MUST use the exact parameter names 'target_tool' and 'payload'. " +
            "Do NOT nest payloads, invent new field names, or use 'operation'/'parameters'.",
        prompt: `Your goal is to test the discovery and execution of tools. ` +
            `Please fetch the content of this URL as markdown: ${targetUrl}. ` +
            `CRITICAL: Do NOT output the full markdown content. ` +
            `Instead, after successfully fetching it using the discovered tool, provide a short, 2-3 sentence Overview of what the site is about.`,
        onStepFinish: (step) => {
            const toolCalls = step.toolCalls.map(t => t.toolName).join(", ");
            if (toolCalls) {
                console.log(`[Autonomy] Tool step finished: ${toolCalls}`);
            }
        }
    });

    console.log("\n[Result]:");
    console.log(result.text);

    // Fetch Tools again to show caching
    const finalToolsList = await client.listTools();
    console.log("\n[System] Task complete. Checking cached tools...");
    console.log(`[System] Final Agent tools cached: [${finalToolsList.tools.map(t => t.name).join(", ")}]`);

    // Clean up
    transport.close();
    process.exit(0);
}

main().catch(console.error);
