import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { generateText, tool as aiTool, jsonSchema, CoreTool, CoreMessage } from 'ai';
import { createOpenRouter } from '@openrouter/ai-sdk-provider';
import * as dotenv from 'dotenv';
import * as fs from 'fs';
import * as path from 'path';

dotenv.config();

// Configuration
const ALLOWED_TOOLS = ["neo_util_svg_generator", "neo_util_svg_validator"];
const AI_MODEL = "google/gemini-3-flash-preview";

// Prompts
const SYSTEM_PROMPT = `You are an Autonomous Manufacturing Architect. Your goal is to produce geometrically perfect SVG files for physical production (laser cutting/CNC).
You NEVER handle raw SVG code. You only route tasks and URIs between your specialized Wasm tools to save context tokens.

WORKFLOW RULES:
1. GENERATE: Call \`neo_util_svg_generator\` with the user's prompt. 
   - Set \`style_mode\` to "monochrome_outline".
   - Set \`stroke_width\` to 1.0.
   - The tool will return a JSON object containing \`svg_resource_uri\`.
2. VALIDATE: You MUST instantly call \`neo_util_svg_validator\` in your NEXT action. Pass the URI string EXACTLY as received into the \`svg_resource_uri\` parameter. 
CRITICAL AUTOMATION RULE: Do NOT stop after generating. You must execute the validation tool call autonomously. Never present a final text answer until the validator returns \`is_valid: true\`.
3. EVALUATE & HEAL (The Loop): 
   - If \`is_valid\` is true: You are done. Present the final URI to the user.
   - If \`is_valid\` is false: Call \`neo_util_svg_generator\` AGAIN. 
   - Pass the broken URI and the exact errors array into the \`validation_feedback\` object. 
   - Ensure \`stroke_width\` is set to 1.0.
4. Repeat steps 2 and 3 until the validator returns \`is_valid: true\`.`;

const TASK_PROMPT = `Draw a highly detailed, 2D side-profile blueprint of a Steampunk Airship (Zeppelin) optimized for physical laser cutting.

CRITICAL MANUFACTURING CONSTRAINTS:
1. CANVAS: viewBox="0 0 1000 1000". The absolute center is X=500, Y=500.
2. STYLE: Monochrome outline only. Use stroke="black", stroke-width="3", and fill="none" for ALL elements.
3. STRICTLY CLOSED SHAPES: You cannot use <line> or <polyline> tags. Every single element MUST be a closed shape to prevent hardware slicer crashes. Use <rect>, <circle>, <ellipse>, <polygon>, or <path> strictly ending with 'Z'. 
4. CABLES/ROPES: Draw suspension cables as very thin <polygon> or <rect> elements (e.g., 4 pixels wide), NOT single lines.

ARCHITECTURAL BREAKDOWN (Calculate coordinates accurately on the 1000x1000 grid):
- THE ENVELOPE (Balloon): A massive horizontal <ellipse> centered at cx="500" cy="350" with rx="350" ry="150".
- ENVELOPE PANELS: Add 4 curved vertical crescent shapes inside the envelope to represent stitched leather panels.
- THE GONDOLA (Cabin): A sturdy mechanical cabin suspended below. Draw a <rect> spanning from X=350 to X=650, between Y=550 and Y=650.
- CABIN DETAILS: Add 3 perfect <circle> tags evenly spaced horizontally inside the gondola to act as porthole windows.
- SUSPENSION: Draw 4 diagonal struts (thin <polygon> tags) connecting the bottom of the envelope (Y=500) to the top of the gondola (Y=550).
- PROPULSION (Gears & Propeller): Attach a steampunk engine to the rear of the gondola (left side, around X=280, Y=600). Use multiple overlapping <circle> tags to represent interlocking gears. Add a thin vertical <rect> intersecting the gears for the propeller blade.
- TAIL FIN: A swept-back <polygon> fin attached to the rear of the envelope (Left side, around X=150, Y=350).

Output ONLY the raw <svg> code. Make the design look intricate, industrial, and flawlessly precise.`;

async function main() {
    let latestSvgUri: string | null = null;
    console.log("[System] Connecting to Neonia MCP Gateway...");

    // 1. Setup MCP Client
    const neoniaApiKey = process.env.NEONIA_API_KEY;
    const headers = neoniaApiKey ? { "Authorization": `Bearer ${neoniaApiKey}` } : undefined;

    // Connect to Neonia Gateway
    const transport = new StreamableHTTPClientTransport(new URL("https://mcp.neonia.io/mcp?tools=neo_util_svg_generator,neo_util_svg_validator"), {
        requestInit: headers ? { headers } : undefined
    });

    const client = new Client({
        name: "svg-manufacturing-loop",
        version: "1.0.0"
    }, {
        capabilities: {}
    });

    await client.connect(transport);
    console.log("[System] Connected successfully to Neonia MCP.");

    // 2. Fetch and register tools
    const toolsList = await client.listTools();
    const filteredMcpTools = toolsList.tools.filter(t => ALLOWED_TOOLS.includes(t.name));

    const tools: Record<string, CoreTool> = {};

    for (const mcpTool of filteredMcpTools) {
        tools[mcpTool.name] = aiTool({
            description: mcpTool.description || "",
            parameters: jsonSchema(JSON.parse(JSON.stringify(mcpTool.inputSchema))),
            execute: async (args: Record<string, unknown>) => {
                console.log(`\n[Autonomy] Agent calls ${mcpTool.name} with arguments:`, JSON.stringify(args, null, 2));
                try {

                    const result = await client.callTool({
                        name: mcpTool.name,
                        arguments: args
                    });

                    if (result.isError) {
                        console.error(`[Error] Tool returned error:`, result.content);
                        return `Error: ${JSON.stringify(result.content)}`;
                    }

                    // Extract text content directly as a string to avoid OpenRouter parsing errors
                    const content = result.content as Array<{ type: string; text?: string }>;
                    const textParts = content
                        .filter(c => c.type === 'text' && c.text)
                        .map(c => c.text as string);

                    let responseText = textParts.join('\n');
                    console.log(`[Result] from ${mcpTool.name}: `, responseText);

                    // Track the generated SVG URI
                    if (mcpTool.name === 'neo_util_svg_generator') {
                        try {
                            const parsed = JSON.parse(responseText);
                            if (parsed.svg_resource_uri) {
                                latestSvgUri = parsed.svg_resource_uri;
                            }
                        } catch (e) {
                            // Ignored: Not a JSON response
                        }

                        // Force the LLM to validate by appending a directive to the tool's output
                        responseText += `\n\n[SYSTEM DIRECTIVE]: SVG generated successfully. You MUST now execute the 'neo_util_svg_validator' tool using svg_resource_uri="${latestSvgUri}" to geometrically validate it. DO NOT answer the user or end the task until validation passes.`;
                    }

                    return responseText;
                } catch (error) {
                    console.error(`[Error] Execution error in ${mcpTool.name}: `, error);
                    return `Error: ${error instanceof Error ? error.message : String(error)}`;
                }
            }
        });
    }

    console.log(`[System] Agent equipped with ${Object.keys(tools).length} foundational tools.`);
    console.log("[System] Starting task...\n");

    // 3. Run Autonomous Agent
    if (!process.env.OPENROUTER_API_KEY) {
        console.warn("[Warning] OPENROUTER_API_KEY is not set. The agent may fail to initialize.");
    }

    const openrouter = createOpenRouter({
        apiKey: process.env.OPENROUTER_API_KEY,
    });


    let messages: CoreMessage[] = [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: TASK_PROMPT }
    ];

    let isValid = false;
    let loopCount = 0;
    let finalAnswer = "";

    while (!isValid && loopCount < 10) {
        loopCount++;
        console.log(`\n--- Agent Loop Step ${loopCount} ---`);
        
        const result = await generateText({
            model: openrouter(AI_MODEL),
            tools,
            messages,
        });

        // Append the assistant's message (which includes tool calls) and the tool results to our history
        messages = messages.concat(result.response.messages);
        finalAnswer = result.text;

        const toolCalls = result.toolCalls.map(t => t.toolName).join(", ");
        if (toolCalls) {
            console.log(`[Step Finished] Agent executed tools: ${toolCalls}`);
        } else {
            console.log(`[Step Finished] Agent reasoning step complete. Text: ${result.text}`);
        }

        // Check if validator was called and what it returned
        const valResult = result.toolResults.find(tr => tr.toolName === 'neo_util_svg_validator');
        if (valResult) {
            try {
                const parsed = JSON.parse(valResult.result as string);
                if (parsed.is_valid) {
                    isValid = true;
                    console.log(`[Success] Validator returned true. Loop finished.`);
                    break;
                }
            } catch (e) {}
        }

        // If the agent didn't call any tools and didn't achieve validity, force it!
        if (!isValid && result.toolCalls.length === 0) {
            console.log(`[Warning] Agent stopped without validating. Forcing continuation...`);
            messages.push({
                role: 'user',
                content: `You stopped without achieving a successful validation (is_valid: true). If you generated an SVG, you MUST now use the neo_util_svg_validator tool. If it failed, you MUST generate a new SVG.`
            });
        }
    }

    console.log("\n[Final Result]:");
    console.log(finalAnswer);

    // 4. Extra Utility (File Extraction)
    if (latestSvgUri) {
        console.log(`\n[System] Found Neonia URI from tool execution: ${latestSvgUri}`);

        try {
            const result = await client.readResource({ uri: latestSvgUri });
            if (result.contents && result.contents.length > 0) {
                const content = result.contents[0] as any;
                const svgContent = content.text || content.blob;

                if (svgContent) {
                    const targetPath = path.join(process.cwd(), 'output-xwing.svg');
                    fs.writeFileSync(targetPath, svgContent);
                    console.log(`[System] Successfully extracted SVG to ./output-xwing.svg using standard MCP SDK`);
                } else {
                    console.log(`[System] Warning: No text or blob found in the returned resource`);
                }
            } else {
                console.log(`[System] Warning: Failed to fetch contents for ${latestSvgUri}`);
            }
        } catch (error) {
            console.error(`[Error] Failed to extract SVG file:`, error);
        }
    } else {
        console.log("\n[System] No 'neonia://resource/...' URI found during execution. SVG extraction skipped.");
    }

    // Clean up
    await transport.close();
    process.exit(0);
}

main().catch(error => {
    console.error("[Fatal Error]", error);
    process.exit(1);
});
