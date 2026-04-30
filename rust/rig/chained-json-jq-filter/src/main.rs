use dotenv::dotenv;
use rig::providers::openai::{Client as OpenAiClient};
use rig::client::CompletionClient;
use rig::completion::Prompt;
use std::env;
use std::error::Error;
use tracing_subscriber::{EnvFilter, FmtSubscriber};

use rmcp::model::{ClientInfo, ClientCapabilities, Implementation};
use rmcp::ServiceExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    // Set up basic tracing to see intermediate tool calls
    let env_filter = std::env::var("RUST_LOG").unwrap_or_else(|_| "rig=info".to_string());
    let subscriber = FmtSubscriber::builder()
        .with_env_filter(EnvFilter::new(env_filter))
        .finish();
    tracing::subscriber::set_global_default(subscriber)
        .expect("setting default subscriber failed");

    dotenv().ok();

    println!("[System] Connecting to Neonia MCP Gateway via rmcp...");

    let url = "https://mcp.neonia.io/mcp?tools=neo_web_json_fetch,neo_data_jq_filter";
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
            "You are an autonomous agent equipped with Neonia's data processing tools.\n\
            ## Usage Guidelines\n\
            1. When asked to process JSON from a URL, ALWAYS use `neo_web_json_fetch` first. It will securely store the file and return a `resource_uri` and a TypeScript schema of the data.\n\
            2. Once you have the `resource_uri` and the schema, use `neo_data_jq_filter` to extract exactly what you need. Pass the `resource_uri` to the `resource_uri` parameter, and formulate a mathematically precise `jq_query` based on the schema.\n\
            3. Write correct JQ queries. If the JSON has a wrapper object like `.posts`, use appropriate mapping. Example: `.posts[0:10] | map({title: .title, body: .body})`.\n\
            4. Self-Correction: If a tool returns an error, evaluate your parameters, fix them, and try again."
        )
        .default_max_turns(5)
        .rmcp_tools(tools, client.peer().to_owned())
        .build();

    let target_url = "https://dummyjson.com/posts";
    let prompt = format!("Fetch the JSON from {}, then use the jq filter to extract the title and body of the first 10 posts. Finally, provide a brief summary of the posts.", target_url);
    
    let response = agent.prompt(&prompt).await?;
    
    println!("\n[Result]:");
    println!("{}", response);

    Ok(())
}
