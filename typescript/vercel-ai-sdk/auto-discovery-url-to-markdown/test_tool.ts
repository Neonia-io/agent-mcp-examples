import { tool as aiTool } from 'ai';
import { z } from 'zod';

const myTool = aiTool({
    description: "Search",
    parameters: z.object({
        query: z.string()
    }),
    execute: async ({ query }) => {
        return query;
    }
});
