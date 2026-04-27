use tracing_subscriber::fmt::format::Writer;
use tracing_subscriber::fmt::FmtContext;
use tracing_subscriber::registry::LookupSpan;
use tracing::Event;
use tracing_subscriber::field::Visit;
use tracing::field::Field;

struct TruncateVisitor<'a> {
    writer: Writer<'a>,
}

impl<'a> Visit for TruncateVisitor<'a> {
    fn record_debug(&mut self, field: &Field, value: &dyn std::fmt::Debug) {
        let s = format!("{:?}", value);
        if s.len() > 100 {
            let _ = write!(self.writer, " {}={:?}...", field.name(), &s[..100]);
        } else {
            let _ = write!(self.writer, " {}={}", field.name(), s);
        }
    }
}
