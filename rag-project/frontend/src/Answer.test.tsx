import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Answer } from "./Answer";
import { answer } from "./fixtures";

describe("Answer", () => {
  it("shows the answer with its citation markers and sources", () => {
    render(<Answer result={answer()} />);
    expect(screen.getByText(/Loosen the lug nuts.*\[SOURCE 1\]/)).toBeTruthy();
    expect(screen.getByText("aventro_manual.pdf")).toBeTruthy();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("renders markup from documents as text, never as HTML", () => {
    const { container } = render(
      <Answer result={answer({ answer: '<img src=x onerror="alert(1)"> **bold**', sources: ["<b>x</b>.pdf"] })} />,
    );
    expect(container.querySelector("img, b")).toBeNull();
    expect(screen.getByText('<img src=x onerror="alert(1)"> **bold**')).toBeTruthy();
  });

  it("shows an abstain clearly and hides the canned abstain text", () => {
    render(
      <Answer
        result={answer({
          outcome: "abstain",
          answer: "I don't have enough information.",
          confidence: null,
          citation_check: null,
          sufficiency: { sufficient: false, reason: "Nothing about brakes.", tier: "llm_judge" },
        })}
      />,
    );
    expect(screen.getByRole("status").textContent).toMatch(/Not answered.*not contain enough.*Nothing about brakes/);
    expect(screen.queryByText("I don't have enough information.")).toBeNull();
    expect(screen.getByText("Documents searched")).toBeTruthy();
  });

  it("shows an empty retrieval as not answered", () => {
    render(<Answer result={answer({ outcome: "empty", sources: [], sufficiency: null })} />);
    expect(screen.getByRole("status").textContent).toMatch(/Nothing relevant was found/);
  });

  it("flags low confidence with the unsupported claims", () => {
    render(
      <Answer
        result={answer({
          outcome: "answer_low_confidence",
          confidence: "low",
          citation_check: { grounded: false, unsupported_claims: ["Torque is 200 Nm."], reason: "x", tier: "llm_judge" },
        })}
      />,
    );
    expect(screen.getByRole("status").textContent).toMatch(/Low confidence.*Torque is 200 Nm\./);
  });

  it("keeps the low-confidence flag on a cache hit", () => {
    render(<Answer result={answer({ outcome: "cached", confidence: "low" })} />);
    expect(screen.getByRole("status").textContent).toMatch(/Low confidence/);
    expect(screen.getByText(/From cache/)).toBeTruthy();
  });
});
