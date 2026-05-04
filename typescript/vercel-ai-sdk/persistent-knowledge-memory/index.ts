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
    const transport = new StreamableHTTPClientTransport(new URL("https://mcp.neonia.io/mcp?tools=neo_sys_memory_lesson,neo_sys_memory_search"), {
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

    // Create Vercel AI SDK tools that explicitly wrap Cloud Memory
    const tools = {
        neo_sys_memory_lesson: aiTool({
            description: "WRITE-ONLY: Store a hard-learned lesson, bug fix, or mandatory rule for future reference.",
            parameters: z.object({
                observation: z.string().describe("OBSERVATION: What happened? The symptom or context"),
                root_cause: z.string().describe("ROOT CAUSE (WHY): Why did it happen?"),
                decision_rule: z.string().describe("DECISION RULE (WHAT): An imperative strict action for future agents to follow"),
                tags: z.array(z.string()).describe("2-3 keywords for semantic retrieval")
            }),
            execute: async (args) => {
                console.log(`[Memory Tool] Agent executed: neo_sys_memory_lesson`);
                try {
                    const result = await client.callTool({
                        name: "neo_sys_memory_lesson",
                        arguments: args as any
                    });
                    if (result.isError) return `Error: ${JSON.stringify(result.content)}`;
                    const content = result.content as Array<{ type: string; text?: string }>;
                    const toolOutput = content.filter(c => c.type === 'text').map(c => c.text || '').join('\n');

                    // Prevent tool calling loops by explicitly telling the LLM to stop after a successful store
                    return `${toolOutput}\nSUCCESS: Memory saved. You MUST now stop calling tools and reply to the user with 'Acknowledged'.`;
                } catch (error) {
                    return `Error: ${String(error)}`;
                }
            }
        }),
        neo_sys_memory_search: aiTool({
            description: "READ-ONLY: Search the shared Swarm memory. Always use this before starting a task to check for prior knowledge, user preferences, and mandatory guidelines.",
            parameters: z.object({
                query: z.string().describe("Semantic search query or keywords to look for.")
            }),
            execute: async (args) => {
                console.log(`[Memory Tool] Agent executed: neo_sys_memory_search (query='${args.query}')`);
                try {
                    const result = await client.callTool({
                        name: "neo_sys_memory_search",
                        arguments: args as any
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

    const openrouter = createOpenRouter({
        apiKey: process.env.OPENROUTER_API_KEY,
    });
    const model = openrouter('google/gemini-3-flash-preview');

    const systemPrompt = "You are an autonomous agent equipped with Neonia Cloud Memory. \
You suffer from amnesia between sessions. \
CRITICAL: Before you answer ANY user prompt or take any actions, you MUST use `neo_sys_memory_search` to fetch your architectural rules and lessons. \
Do not answer the user without searching your memory first! \
When explicitly asked to remember an architectural lesson, use `neo_sys_memory_lesson`. \
IMPORTANT: Once you execute the memory lesson tool successfully, IMMEDIATELY reply to the user with the final text and do NOT call any more tools.";

    console.log("==================================================");
    console.log("SESSION 1: Storing an architectural lesson (Admin post-mortem)");
    console.log("==================================================");

    const userPrompt1 = "We just had a production outage because the LLM context limit was reached when parsing the Reddit API. " +
        "The root cause is that raw JSON contains too much whitespace and UI metadata. " +
        "Store an architectural lesson that future agents must ALWAYS use the jq filter tool before parsing API output. " +
        "Use tags ['api', 'json', 'optimization'].";

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

    const userPrompt2 = "I need to fetch some user comments from the HackerNews API. How should I approach reading the data? (Hint: Please search your memory for 'api json optimization' rules first!)";
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
