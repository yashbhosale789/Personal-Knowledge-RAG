import { describe, expect, it } from "vitest";
import { MEMORY_ANSWER_CHARS, MEMORY_TURNS, remember } from "./api";
import { answer } from "./fixtures";

describe("remember", () => {
  it("keeps only the question, rewritten question and answer", () => {
    expect(remember([], "How do I change a tyre?", answer())).toEqual([
      {
        query: "How do I change a tyre?",
        rewritten_query: "change a tyre",
        answer: "Loosen the lug nuts before jacking the car [SOURCE 1].",
      },
    ]);
  });

  it("keeps the newest turns and clips long answers by code point", () => {
    let memory = remember([], "q0", answer({ answer: "😀".repeat(MEMORY_ANSWER_CHARS + 10) }));
    expect(Array.from(memory[0].answer)).toHaveLength(MEMORY_ANSWER_CHARS);
    expect(memory[0].answer).toBe("😀".repeat(MEMORY_ANSWER_CHARS));

    for (let i = 1; i <= MEMORY_TURNS + 2; i++) memory = remember(memory, `q${i}`, answer({ rewritten_query: null }));
    expect(memory.map((t) => t.query)).toEqual(["q3", "q4", "q5", "q6", "q7"]);
    expect(memory[0].rewritten_query).toBeNull();
  });
});
