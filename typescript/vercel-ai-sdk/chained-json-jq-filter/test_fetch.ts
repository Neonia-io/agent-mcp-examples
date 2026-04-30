import { generateText, tool as aiTool, jsonSchema } from 'ai';
import { createOpenAI } from '@ai-sdk/openai';
import * as dotenv from 'dotenv';
dotenv.config();

const openrouter = createOpenAI({
    baseURL: 'https://openrouter.ai/api/v1',
    apiKey: process.env.OPENROUTER_API_KEY,
});

async function main() {
    try {
        const result = await generateText({
            model: openrouter('anthropic/claude-3.7-sonnet'),
            tools: {
                "neo_data_jq_filter": aiTool({
                    description: "Processes JSON data dynamically using JQ queries.",
                    parameters: jsonSchema({
                        type: "object",
                        properties: {
                            data_url: { type: "string" },
                            jq_query: { type: "string" },
                            raw_json: { type: "string" }
                        },
                        required: ["jq_query"]
                    }),
                    execute: async (args) => { return "executed"; }
                })
            },
            system: "Test",
            prompt: "Use the tool to process some data."
        });
        console.log("Success:", result.text);
    } catch (e: any) {
        console.error(e.data || e);
    }
}
main();
