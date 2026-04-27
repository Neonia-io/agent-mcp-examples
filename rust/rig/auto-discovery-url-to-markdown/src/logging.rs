use tracing::{Event, Subscriber};
use tracing_subscriber::{
    fmt::{format::Writer, FmtContext, FormatEvent, FormatFields},
    registry::LookupSpan,
};
use tracing_core::Field;
use tracing_subscriber::field::Visit;
use std::fmt;

pub struct TruncatingFormatter;

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
        // Format the metadata (timestamp, level, target, etc)
        let metadata = event.metadata();
        write!(writer, "[{}] {}: ", metadata.level(), metadata.target())?;

        // Format the fields using our custom visitor
        let mut visitor = TruncatingVisitor { writer: writer.by_ref() };
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
        if field.name() == "result" && s.len() > 300 {
            let _ = write!(self.writer, " {}={}... [TRUNCATED]", field.name(), &s[..300]);
        } else if s.len() > 1000 {
            let _ = write!(self.writer, " {}={}... [TRUNCATED]", field.name(), &s[..1000]);
        } else {
            let _ = write!(self.writer, " {}={}", field.name(), s);
        }
    }
}
