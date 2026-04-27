import { generateText } from 'ai';
generateText({
    model: {} as any,
    prompt: "hi",
    onStepFinish: (step) => {
        console.log(step.toolCalls);
    }
});
