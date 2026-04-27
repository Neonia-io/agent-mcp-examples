import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { generateText, tool as aiTool, jsonSchema, stepCountIs } from 'ai';
import { createOpenAI } from '@ai-sdk/openai';
import * as dotenv from 'dotenv';

dotenv.config();

// Patch fetch to log the body
const originalFetch = globalThis.fetch;
globalThis.fetch = async (url, options) => {
    if (url.toString().includes("openrouter")) {
        console.log("SENDING TO OPENROUTER:", JSON.stringify(options?.body ? JSON.parse(options.body as string) : {}, null, 2));
    }
    return originalFetch(url, options);
};

async function main() {
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
    const toolsList = await client.listTools();
    const allowedTools = ["neo_data_jq_filter"];
    const filteredMcpTools = toolsList.tools.filter(t => allowedTools.includes(t.name));

    const tools: Record<string, any> = {};
    for (const mcpTool of filteredMcpTools) {
        tools[mcpTool.name] = aiTool({
            description: mcpTool.description || "",
            parameters: jsonSchema(mcpTool.inputSchema as any),
            execute: async (args: any) => { return "exec"; }
        } as any);
    }

    const targetUrl = "https://dummyjson.com/carts";
    const openrouter = createOpenAI({
        baseURL: 'https://openrouter.ai/api/v1',
        apiKey: process.env.OPENROUTER_API_KEY,
    });
    
    try {
        const result = await generateText({
            model: openrouter('anthropic/claude-3.7-sonnet'),
            tools: tools,
            stopWhen: stepCountIs(5),
            system: "Test System",
            prompt: `Find the total discountedTotal for all carts at this URL: ${targetUrl}`,
        });
        console.log(result.text);
    } catch (e: any) {
        console.error("ERROR", e.data);
    }
    transport.close();
}
main();
