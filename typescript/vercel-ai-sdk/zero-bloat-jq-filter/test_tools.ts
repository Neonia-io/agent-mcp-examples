import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import * as dotenv from 'dotenv';
dotenv.config();

async function main() {
    const neoniaApiKey = process.env.NEONIA_API_KEY;
    const headers = neoniaApiKey ? { "Authorization": `Bearer ${neoniaApiKey}` } : undefined;
    const transport = new StreamableHTTPClientTransport(new URL("https://mcp.neonia.io/mcp?tools=neo_data_jq_filter"), {
        requestInit: headers ? { headers } : undefined
    });
    const client = new Client({ name: "test", version: "1.0.0" }, { capabilities: {} });
    await client.connect(transport);
    const toolsList = await client.listTools();
    console.log(JSON.stringify(toolsList.tools, null, 2));
    transport.close();
}
main();
