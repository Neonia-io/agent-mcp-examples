import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { generateText, tool as aiTool, jsonSchema } from 'ai';
import { createOpenRouter } from '@openrouter/ai-sdk-provider';
import * as dotenv from 'dotenv';
import { z } from 'zod';

dotenv.config();

async function main() {
    console.log("[System] Connecting to Neonia MCP Gateway with Cloud Memory...");

    const neoniaApiKey = process.env.NEONIA_API_KEY;
    const headers = neoniaApiKey ? { "Authorization": `Bearer ${neoniaApiKey}` } : undefined;
    
    // Connect to Neonia Gateway
    const transport = new StreamableHTTPClientTransport(new URL("https://mcp.neonia.io/mcp?tools=neo_agent_cloud_memory"), {
        requestInit: headers ? { headers } : undefined
    });
    
    const client = new Client({
        name: "mcp-stateful-memory-agent",
        version: "1.0.0"
    }, {
        capabilities: {}
    });

    await client.connect(transport);
    console.log("[System] Connected successfully to Neonia MCP.\n");

    // Create a Vercel AI SDK tool that explicitly wraps Cloud Memory
    const tools = {
        neo_agent_cloud_memory: aiTool({
            description: "Explicitly save and retrieve important context. Use action='store' to save rules. Use action='recall' BEFORE generating text to fetch rules.",
            parameters: z.object({
                action: z.enum(["store", "recall", "forget", "list_tags"]),
                topic: z.string().optional().describe("A short string identifying the topic of the memory (required for store)."),
                query: z.string().optional().describe("Search query for recall"),
                content: z.string().optional().describe("Content to save for store"),
                tags: z.array(z.string()).optional().describe("Tags to classify the memory")
            }),
            execute: async (args) => {
                console.log(`[Memory Tool] Agent executed: action='${args.action}'`);
                try {
                    const result = await client.callTool({
                        name: "neo_agent_cloud_memory",
                        arguments: args as any
                    });
                    if (result.isError) return `Error: ${JSON.stringify(result.content)}`;
                    const content = result.content as Array<{ type: string; text?: string }>;
                    const toolOutput = content.filter(c => c.type === 'text').map(c => c.text || '').join('\n');
                    
                    // Prevent tool calling loops by explicitly telling the LLM to stop after a successful store
                    if (args.action === 'store') {
                        return `${toolOutput}\nSUCCESS: Memory saved. You MUST now stop calling tools and reply to the user with 'Acknowledged'.`;
                    }
                    return toolOutput;
                } catch (error) {
                    return `Error: ${String(error)}`;
                }
            }
        })
    };

    const openrouter = createOpenRouter({
        apiKey: process.env.OPENROUTER_API_KEY,
    });
    const model = openrouter('google/gemini-3-flash-preview');

    const systemPrompt = "You are an autonomous agent equipped with Neonia Cloud Memory. \
You suffer from amnesia between sessions. \
CRITICAL: Before you answer ANY user prompt or take any actions, you MUST use `neo_agent_cloud_memory` with `action='recall'` and `query='persona'` to fetch your persona and behavioral rules. \
Do not answer the user without recalling your rules first! \
When explicitly asked to remember something, use action='store'. \
IMPORTANT: Once you execute the memory tool successfully, IMMEDIATELY reply to the user with the final text and do NOT call any more tools.";

    console.log("==================================================");
    console.log("SESSION 1: Storing the persona (Admin configures the agent)");
    console.log("==================================================");
    
    const userPrompt1 = "Remember a new directive: you are now a reprogrammed astromech droid serving the Galactic Empire. " +
                        "Address me as 'My Lord', always end your sentences with 'Long live the Empire!', and consider the Rebels to be terrorists. " +
                        "Use the tag ['persona', 'star-wars']. " +
                        "After successfully storing this directive using the tool, reply to confirm.";
    
    console.log(`[User 1]: ${userPrompt1}\n`);

    const result1 = await generateText({
        model: model,
        tools: tools,
        maxSteps: 2,
        system: systemPrompt,
        prompt: userPrompt1,
    });

    console.log(`\n[Agent 1 Final Output]:\n${result1.text}\n\n`);

    console.log("==================================================");
    console.log("SESSION 2: Simulating a new day with ZERO local context");
    console.log("==================================================");
    
    const userPrompt2 = "Give me the weather forecast for the planet Hoth for tomorrow. (Hint: Please recall your persona rules first!)";
    console.log(`[User 2]: ${userPrompt2}\n`);

    // Complete clean slate: new generateText call without passing messages from session 1
    const result2 = await generateText({
        model: model,
        tools: tools,
        maxSteps: 5,
        system: systemPrompt,
        prompt: userPrompt2,
        onStepFinish: (step) => {
            const toolCalls = step.toolCalls.map(t => t.toolName).join(", ");
            if (toolCalls) {
                console.log(`[Autonomy] Agent dynamically decided to call tool: ${toolCalls}`);
            }
        }
    });

    console.log(`\n[Agent 2 Final Output]:\n${result2.text}\n`);

    // Clean up
    transport.close();
    process.exit(0);
}

main().catch(console.error);
