import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Answer } from "./Answer";
import { answer } from "./fixtures";

const expandSources = (name: RegExp) => fireEvent.click(screen.getByRole("button", { name }));

describe("Answer", () => {
  it("shows [SOURCE N] markers as numbered badges and folds the sources away", () => {
    render(<Answer result={answer()} />);
    expect(screen.getByText(/before jacking the car/).textContent).toBe("Loosen the lug nuts before jacking the car 1.");
    expect(screen.getByTitle("Source 1").textContent).toBe("1");
    expect(screen.queryByRole("listitem")).toBeNull();
    expect(screen.getByText("High confidence")).toBeTruthy();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("expands the sources with file, page, snippet and a cited mark", () => {
    render(<Answer result={answer()} />);
    const chip = screen.getByRole("button", { name: /2 sources/ });
    expect(chip.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(chip);
    expect(chip.getAttribute("aria-expanded")).toBe("true");
    const [first, second] = screen.getAllByRole("listitem");
    expect(first.textContent).toBe("1aventro_manual.pdf · page 12Loosen each lug nut half a turn.cited");
    expect(first.className).toBe("cited");
    expect(second.textContent).toBe("2warranty.pdfTyres are not covered.");
    fireEvent.click(chip);
    expect(screen.queryByRole("listitem")).toBeNull();
  });

  it("renders markup from documents as text, never as HTML", () => {
    const { container } = render(
      <Answer
        result={answer({
          answer: '<img src=x onerror="alert(1)"> **bold**',
          chunks: [{ n: 1, source: "<b>x</b>.pdf", page: null, snippet: "<script>alert(1)</script>", cited: true }],
        })}
      />,
    );
    expandSources(/1 source/);
    expect(container.querySelector("img, b, script")).toBeNull();
    expect(screen.getByText('<img src=x onerror="alert(1)"> **bold**')).toBeTruthy();
    expect(screen.getByText("<script>alert(1)</script>")).toBeTruthy();
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
    expect(screen.getByRole("button", { name: /2 documents searched/ })).toBeTruthy();
    expect(screen.queryByText("High confidence")).toBeNull();
  });

  it("shows an empty retrieval as not answered", () => {
    render(<Answer result={answer({ outcome: "empty", chunks: [], sufficiency: null })} />);
    expect(screen.getByRole("status").textContent).toMatch(/Nothing relevant was found/);
    expect(screen.queryByRole("button")).toBeNull();
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
    expect(screen.queryByText("High confidence")).toBeNull();
  });

  it("keeps the low-confidence flag on a cache hit", () => {
    render(<Answer result={answer({ outcome: "cached", confidence: "low" })} />);
    expect(screen.getByRole("status").textContent).toMatch(/Low confidence/);
    expect(screen.getByText(/From cache/)).toBeTruthy();
  });
});
