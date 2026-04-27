#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::DEBUG)
        .init();
    dotenv::dotenv().ok();
    use rig::providers::openai::Client as OpenAiClient;
    use rig::client::CompletionClient;
    use rig::completion::Prompt;
    use rmcp::model::{ClientInfo, ClientCapabilities, Implementation};
    use rmcp::ServiceExt;
    
    let url = "https://mcp.neonia.io/mcp?tools=neo_agent_tool_discovery,neo_agent_tool_execute";
    let neonia_key = std::env::var("NEONIA_API_KEY").unwrap_or_default();
    let mut config = rmcp::transport::streamable_http_client::StreamableHttpClientTransportConfig::with_uri(url);
    config.auth_header = Some(format!("Bearer {}", neonia_key));
    let transport = rmcp::transport::StreamableHttpClientTransport::from_config(config);
    
    let client_info = ClientInfo::new(ClientCapabilities::default(), Implementation::new("test", "0.1"));
    let client = client_info.serve(transport).await?;
    
    let tools = client.list_tools(Default::default()).await?.tools;
    println!("Initial tools: {:?}", tools.iter().map(|t| t.name.clone()).collect::<Vec<_>>());
    
    let openrouter_client = OpenAiClient::builder()
        .api_key(std::env::var("OPENROUTER_API_KEY").unwrap_or_else(|_| "dummy_key".to_string()).as_str())
        .base_url("https://openrouter.ai/api/v1")
        .build().unwrap();

    let agent = openrouter_client.agent("anthropic/claude-3.7-sonnet")
        .default_max_turns(5)
        .rmcp_tools(tools, client.peer().to_owned())
        .build();
        
    let response = agent.prompt("I need to fetch this URL as markdown: https://neonia.io. Please use discovery to find a tool, then execute it.").await?;
    println!("Response: {}", response);
    Ok(())
}
