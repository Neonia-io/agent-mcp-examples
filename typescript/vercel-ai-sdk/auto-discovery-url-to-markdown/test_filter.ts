interface TextContent { type: "text"; text: string; }
interface ImageContent { type: "image"; data: string; }
type Content = TextContent | ImageContent;

const content: Content[] = [];
content.filter(c => c.type === 'text').map(c => c.text);
