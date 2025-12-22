export type StepType = 'tool' | 'thought';

export interface ToolStep {
    type: StepType;
    name: string; // For tools: tool name; For thought: "Thinking"
    source: string; // e.g. "supervisor", "sql_agent"
    
    // For Tools
    input?: string;
    output?: string;
    status: 'running' | 'completed' | 'error';
    
    // For Thoughts
    thought?: string; // Content of the thought
    
    // For nesting
    subSteps?: ToolStep[]; 
}

export interface Message {
    role: 'user' | 'assistant';
    content: string;
    isStreaming?: boolean;
    steps?: ToolStep[]; // Top-level steps (from supervisor)
}

export interface Session {
    id: string;
    title: string;
    created_at: string;
    updated_at: string;
}
