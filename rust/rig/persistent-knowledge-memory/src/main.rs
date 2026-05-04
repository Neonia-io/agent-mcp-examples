use dotenv::dotenv;
use rig::providers::openai::Client as OpenAiClient;
use rig::client::CompletionClient;
use rig::completion::Prompt;
use std::env;
use std::error::Error;
use tracing_subscriber::{EnvFilter, FmtSubscriber};

use rmcp::model::{ClientInfo, ClientCapabilities, Implementation};
use rmcp::ServiceExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    // Set up basic tracing to see tool calls
    let env_filter = std::env::var("RUST_LOG").unwrap_or_else(|_| "rig=info".to_string());
    let subscriber = FmtSubscriber::builder()
        .with_env_filter(EnvFilter::new(env_filter))
        .finish();
    tracing::subscriber::set_global_default(subscriber)
        .expect("setting default subscriber failed");

    dotenv().ok();

    println!("[System] Connecting to Neonia MCP Gateway with Cloud Memory...");

    let url = "https://mcp.neonia.io/mcp?tools=neo_sys_memory_lesson,neo_sys_memory_search";
    let neonia_key = env::var("NEONIA_API_KEY").unwrap_or_default();
    
    let mut config = rmcp::transport::streamable_http_client::StreamableHttpClientTransportConfig::with_uri(url);
    config.auth_header = Some(format!("Bearer {}", neonia_key));
    
    let transport = rmcp::transport::StreamableHttpClientTransport::from_config(config);
    
    let capabilities = ClientCapabilities::default();
    let impl_info = Implementation::new("rig-stateful-agent", "0.1.0");
    let client_info = ClientInfo::new(capabilities, impl_info);
    
    let client = client_info.serve(transport).await?;
    println!("[System] Connected successfully to Neonia MCP.\n");

    let openrouter_api_key = env::var("OPENROUTER_API_KEY").unwrap_or_else(|_| "dummy_key".to_string());
    let openrouter_client = OpenAiClient::builder()
        .api_key(openrouter_api_key.as_str())
        .base_url("https://openrouter.ai/api/v1")
        .build()
        .expect("Failed to build OpenAI client");

    let initial_tools = client.list_tools(Default::default()).await?.tools;

    let system_prompt = "You are an autonomous agent equipped with Neonia Cloud Memory. \
                         You suffer from amnesia between sessions. \
                         CRITICAL: Before you answer ANY user prompt or take any actions, you MUST use `neo_sys_memory_search` to fetch your architectural rules and lessons. \
                         Do not answer the user without searching your memory first! \
                         When explicitly asked to remember an architectural lesson, use `neo_sys_memory_lesson`.";

    println!("==================================================");
    println!("SESSION 1: Storing an architectural lesson (Admin post-mortem)");
    println!("==================================================");

    // Create Agent for Session 1
    let agent_1 = openrouter_client.agent("google/gemini-3-flash-preview")
        .preamble(system_prompt)
        .default_max_turns(5)
        .rmcp_tools(initial_tools.clone(), client.peer().to_owned())
        .build();

    let user_prompt_1 = "We just had a production outage because the LLM context limit was reached when parsing the Reddit API. \
                         The root cause is that raw JSON contains too much whitespace and UI metadata. \
                         Store an architectural lesson that future agents must ALWAYS use the jq filter tool before parsing API output. \
                         Use tags ['api', 'json', 'optimization'].";
    
    println!("[User 1]: {}\n", user_prompt_1);
    
    let response_1 = agent_1.prompt(user_prompt_1).await?;
    println!("\n[Agent 1 Final Output]:\n{}\n\n", response_1);

    println!("==================================================");
    println!("SESSION 2: Simulating a new day with ZERO local context");
    println!("==================================================");

    // Create a completely new Agent for Session 2 with NO history from agent_1
    let agent_2 = openrouter_client.agent("google/gemini-3-flash-preview")
        .preamble(system_prompt)
        .default_max_turns(5)
        .rmcp_tools(initial_tools.clone(), client.peer().to_owned())
        .build();

    let user_prompt_2 = "I need to fetch some user comments from the HackerNews API. How should I approach reading the data? (Hint: Please search your memory for 'api json optimization' rules first!)";
    println!("[User 2]: {}\n", user_prompt_2);

    let response_2 = agent_2.prompt(user_prompt_2).await?;
    println!("\n[Agent 2 Final Output]:\n{}\n", response_2);

    Ok(())
}
