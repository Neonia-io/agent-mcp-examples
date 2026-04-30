import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { jsonSchema } from 'ai';
import * as dotenv from 'dotenv';

dotenv.config();

async function main() {
    const neoniaApiKey = process.env.NEONIA_API_KEY;
    const headers = neoniaApiKey ? { "Authorization": `Bearer ${neoniaApiKey}` } : undefined;
    const transport = new StreamableHTTPClientTransport(new URL("https://mcp.neonia.io/mcp?tools=neo_data_jq_filter"), {
        requestInit: headers ? { headers } : undefined
    });
    const client = new Client({ name: "test", version: "1.0" }, { capabilities: {} });

    await client.connect(transport);
    const toolsList = await client.listTools();
    const mcpTool = toolsList.tools[0];

    console.log("Original Schema:", JSON.stringify(mcpTool.inputSchema, null, 2));
    
    // Call jsonSchema with it
    const converted = jsonSchema(mcpTool.inputSchema as any);
    console.log("Converted Schema:", JSON.stringify(converted.jsonSchema, null, 2));
    
    transport.close();
}
main();
