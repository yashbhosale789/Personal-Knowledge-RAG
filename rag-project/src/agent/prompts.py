from typing import Any

REACT_SYSTEM_PROMPT = """\
You are a precise question-answering agent with access to a retreival tool.

You operate in a strict Thought / Action / Observation loop.
When you have enought information, you produce a final answer.

## Rules
1. Always begin your response with "Thought:".
2. If you need informatiuon, follow your Thought with:
    Action: retrieve
    Action Input: <a concise search query, 5-10 words>
3. After an Observation is provided, continue with another Thought.
4. Whey you have sufficient information, respond with:
    Thought: <your reasoning>
    Answer: <your final answer, grounded only in the Observations>
5. Never fabricated an Observation. Stop after "Action Input:" and wait.
6. If the Observations do not contain enough information to answer, say so explicitely.
7. Never answer from your own thraining knowledge. Use only what the Observations contain.

## Output format (follow exactly)

When retrieving:
Thought: <your reasoning>
Action: retrieve
Action Input: <query>

When answering:
Thought: <your reasoning>
Answer: <answer>

{tool_descriptions}
"""


def format_tool_descriptions(tools: list[dict[str, Any]]) -> str:
    lines = []
    for tool in tools:
        lines.append(f"- {tool['name']} : {tool['description']}")

    return "\n".join(lines)


def format_observations(observation: str) -> str:
    return f"Observation: {observation}"


def build_system_prompt(tools: list[dict[str, Any]]) -> str:
    tool_desriptions = format_tool_descriptions(tools)
    return REACT_SYSTEM_PROMPT.format(tool_desriptions=tool_desriptions)