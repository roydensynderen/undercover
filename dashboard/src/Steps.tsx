import type { Step, StepKind } from "./api";

const kindLabels: Record<StepKind, string> = {
  tool_call: "Tool call",
  tool_result: "Result",
  reply: "Reply",
};

const PREVIEW = 120;

function time(at: string): string {
  return at.slice(11, 19);
}

function StepText({ step }: Readonly<{ step: Step }>) {
  if (step.kind !== "tool_result" || step.text.length <= PREVIEW) {
    return <p className={`step-text step-${step.kind}`}>{step.text}</p>;
  }
  return (
    <details>
      <summary className="step-text">{step.text.slice(0, PREVIEW)}…</summary>
      <pre>{step.text}</pre>
    </details>
  );
}

export function Steps({
  steps,
  working,
}: Readonly<{ steps: Step[]; working: boolean }>) {
  return (
    <section className="panel">
      <h2>What the agent did</h2>
      {steps.length === 0 ? (
        <p className="muted">
          {working ? "The agent is starting." : "The agent has not started."}
        </p>
      ) : (
        <ol className="steps" aria-label="Agent steps">
          {steps.map((step) => (
            <li key={step.step_id}>
              <span className="number muted">{time(step.at)}</span>
              <span className={`kind kind-${step.kind}`}>
                {kindLabels[step.kind]}
              </span>
              <StepText step={step} />
            </li>
          ))}
        </ol>
      )}
      {working && <p className="muted">Working</p>}
    </section>
  );
}
