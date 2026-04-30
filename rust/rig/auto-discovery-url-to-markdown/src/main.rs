use dotenv::dotenv;
use rig::providers::openai::Client as OpenAiClient;
use rig::client::CompletionClient;
use rig::completion::Prompt;
use std::env;
use std::error::Error;
use tracing_subscriber::{EnvFilter, FmtSubscriber};

use rmcp::model::{ClientInfo, ClientCapabilities, Implementation};
use rmcp::ServiceExt;
use tracing::{Event, Subscriber};
use tracing_subscriber::{
    fmt::{format::Writer, FmtContext, FormatEvent, FormatFields},
    registry::LookupSpan,
};
use tracing::field::Field;
use tracing_subscriber::field::Visit;
use std::fmt;

struct TruncatingFormatter;

impl<S, N> FormatEvent<S, N> for TruncatingFormatter
where
    S: Subscriber + for<'a> LookupSpan<'a>,
    N: for<'a> FormatFields<'a> + 'static,
{
    fn format_event(
        &self,
        ctx: &FmtContext<'_, S, N>,
        mut writer: Writer<'_>,
        event: &Event<'_>,
    ) -> fmt::Result {
        let metadata = event.metadata();
        write!(writer, "[{}] {}: ", metadata.level(), metadata.target())?;
        let mut visitor = TruncatingVisitor { writer: &mut writer };
        event.record(&mut visitor);
        writeln!(writer)
    }
}

struct TruncatingVisitor<'a, 'writer> {
    writer: &'a mut Writer<'writer>,
}

impl<'a, 'writer> Visit for TruncatingVisitor<'a, 'writer> {
    fn record_debug(&mut self, field: &Field, value: &dyn fmt::Debug) {
        let s = format!("{:?}", value);
        if field.name() == "result" && s.len() > 200 {
            let _ = write!(self.writer, " {}={:?}... [TRUNCATED]", field.name(), &s[..200]);
        } else if s.len() > 1000 {
            let _ = write!(self.writer, " {}={:?}... [TRUNCATED]", field.name(), &s[..1000]);
        } else {
            let _ = write!(self.writer, " {}={}", field.name(), s);
        }
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    // Set up tracing with our custom truncating formatter to hide massive tool results
    let env_filter = std::env::var("RUST_LOG").unwrap_or_else(|_| "rig=info,mcp_auto_discovery_agent=info".to_string());
    let subscriber = FmtSubscriber::builder()
        .with_env_filter(EnvFilter::new(env_filter))
        .event_format(TruncatingFormatter)
        .finish();
    tracing::subscriber::set_global_default(subscriber)
        .expect("setting default subscriber failed");

    dotenv().ok();

    println!("[System] Connecting to Neonia MCP Gateway with Auto-Pilot Tools...");

    // neo_sys_tool_discovery and neo_sys_tool_execute are system tools that are available by default.
    // There is no need to explicitly request them in the URL.
    let url = "https://mcp.neonia.io/mcp";
    let neonia_key = env::var("NEONIA_API_KEY").unwrap_or_default();
    
    let mut config = rmcp::transport::streamable_http_client::StreamableHttpClientTransportConfig::with_uri(url);
    config.auth_header = Some(format!("Bearer {}", neonia_key));
    
    let transport = rmcp::transport::StreamableHttpClientTransport::from_config(config);
    
    let capabilities = ClientCapabilities::default();
    let impl_info = Implementation::new("rig-agent", "0.1.0");
    let client_info = ClientInfo::new(capabilities, impl_info);
    
    let client = client_info.serve(transport).await?;
    println!("[System] Connected successfully to Neonia MCP.");

    // Fetch initial tools
    let initial_tools = client.list_tools(Default::default()).await?.tools;
    println!("[System] Initial Agent tools cached: {:?}\n", initial_tools.iter().map(|t| t.name.clone()).collect::<Vec<_>>());

    println!("[System] Starting task...\n");

    let openrouter_api_key = env::var("OPENROUTER_API_KEY").unwrap_or_else(|_| "dummy_key".to_string());
    let openrouter_client = OpenAiClient::builder()
        .api_key(openrouter_api_key.as_str())
        .base_url("https://openrouter.ai/api/v1")
        .build()
        .expect("Failed to build OpenAI client");

    let agent = openrouter_client.agent("google/gemini-3-flash-preview")
        .preamble(
            "You are an autonomous agent equipped with Neonia's auto-pilot capabilities. \
            If you need a tool you do not have, use `neo_sys_tool_discovery` to find it, \
            and then explicitly run it using `neo_sys_tool_execute` without asking the user. \
            Do NOT assume you have any tools other than what is explicitly in your tool list."
        )
        .default_max_turns(5)
        .rmcp_tools(initial_tools, client.peer().to_owned())
        .build();

    // We use the real neonia.io site to showcase that our custom TruncatingFormatter
    // successfully prevents the massive Markdown output from spamming the console logs.
    let target_url = "https://neonia.io";
    let prompt = format!(
        "Your goal is to test the discovery and execution of tools. \
        Please fetch the content of this URL as markdown: {}. \
        CRITICAL: Do NOT output the full markdown content. \
        Instead, after successfully fetching it using the discovered tool, provide a short, 2-3 sentence Overview of what the site is about.", 
        target_url
    );
    
    let response = agent.prompt(&prompt).await?;
    
    println!("\n[Result]:");
    println!("{}\n", response);

    // Fetch Tools again to show caching
    let final_tools = client.list_tools(Default::default()).await?.tools;
    println!("[System] Task complete. Checking cached tools...");
    println!("[System] Final Agent tools cached: {:?}", final_tools.iter().map(|t| t.name.clone()).collect::<Vec<_>>());

    Ok(())
}
