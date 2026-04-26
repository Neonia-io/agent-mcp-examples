use dotenv::dotenv;
use rig::providers::openai::{Client as OpenAiClient};
use rig::client::CompletionClient;
use rig::completion::Prompt;
use std::env;
use std::error::Error;

use rmcp::model::{ClientInfo, ClientCapabilities, Implementation};
use rmcp::ServiceExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    dotenv().ok();

    println!("[System] Connecting to Neonia MCP Gateway via rmcp...");

    let url = "https://mcp.neonia.io/mcp?tools=neo_data_jq_filter";
    let neonia_key = env::var("NEONIA_API_KEY").unwrap_or_default();
    
    // Configure the rmcp transport
    let mut config = rmcp::transport::streamable_http_client::StreamableHttpClientTransportConfig::with_uri(url);
    config.auth_header = Some(format!("Bearer {}", neonia_key));
    
    let transport = rmcp::transport::StreamableHttpClientTransport::from_config(config);
    
    let capabilities = ClientCapabilities::default();
    let impl_info = Implementation::new("rig-agent", "0.1.0");
    let client_info = ClientInfo::new(capabilities, impl_info);
    
    let client = client_info.serve(transport).await?;
    println!("[System] Connected successfully to Neonia MCP.");

    // Fetch Tools
    let tools = client.list_tools(Default::default()).await?.tools;
    println!("[System] Agent equipped with {} tools.", tools.len());
    println!("[System] Starting task...\n");

    let openrouter_api_key = env::var("OPENROUTER_API_KEY").unwrap_or_else(|_| "dummy_key".to_string());
    let openrouter_client = OpenAiClient::builder()
        .api_key(openrouter_api_key.as_str())
        .base_url("https://openrouter.ai/api/v1")
        .build()
        .expect("Failed to build OpenAI client");

    let agent = openrouter_client.agent("anthropic/claude-3.7-sonnet")
        .preamble(
            "You are an autonomous agent equipped with the neo_data_jq_filter tool.\n\
            CRITICAL SYSTEM TOOL: This is a core data manipulation capability. ALWAYS use this to extract specific fields or filter arrays from large JSON files instead of trying to parse them entirely inside your context window or hallucinating data structures.\n\
            ## Usage Guidelines\n\
            1. Prefer data_url for large files: If you need to read JSON from a URL (e.g. an API endpoint), pass the URL to data_url and the tool will fetch and process it natively in its memory, completely bypassing your token limits.\n\
            2. Use raw_json for existing data: If you already have the data in a variable or context and just need to query it, pass it as a string to raw_json.\n\
            3. Write correct JQ queries: Pass the filter to jq_query. Examples: .[] | .id, .users[0].name, map(select(.active == true)).\n\
            4. Self-Correction: If the tool returns \"Invalid JQ syntax. Please correct your query.\", evaluate your query string, fix the syntax error, and call the tool again."
        )
        .default_max_turns(5)
        .rmcp_tools(tools, client.peer().to_owned())
        .build();

    let target_url = "https://dummyjson.com/carts";
    let prompt = format!("Find the total discountedTotal for all carts at this URL: {}", target_url);
    
    let response = agent.prompt(&prompt).await?;
    
    println!("\n[Result]:");
    println!("{}", response);

    Ok(())
}
