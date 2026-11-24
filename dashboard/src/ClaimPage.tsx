import { useCallback } from "react";
import {
  api,
  type Claim,
  type Policy,
  type PreviousClaim,
  type Step,
} from "./api";
import { finished, label, money, outcomeLabels } from "./format";
import { SignOffPanel } from "./SignOffPanel";
import { StatusBadge } from "./StatusBadge";
import { Steps } from "./Steps";
import { usePolled } from "./usePolled";

interface Loaded {
  claim: Claim;
  steps: Step[];
}

/** The agent is working until the claim is decided and its last step is its final reply. */
function agentWorking({ claim, steps }: Loaded): boolean {
  const last = steps.at(-1);
  return (
    !finished(claim.status) || (last !== undefined && last.kind !== "reply")
  );
}
const never = () => false;

function paymentText(claim: Claim): string {
  if (claim.payment) return `Paid ${money(claim.payment.amount)}`;
  return claim.decision?.decision === "approve" ? "Not paid" : "None";
}

function DecisionPanel({ claim }: Readonly<{ claim: Claim }>) {
  const { decision } = claim;
  if (!decision) {
    return (
      <section className="panel">
        <h2>Decision</h2>
        <p className="muted">The agent has not decided this claim yet.</p>
      </section>
    );
  }
  return (
    <section className={`panel decision outcome-${decision.decision}`}>
      <h2>Decision: {outcomeLabels[decision.decision]}</h2>
      <dl className="facts">
        <dt>Payout</dt>
        <dd className="number">{money(decision.payout)}</dd>
        <dt>Policy section</dt>
        <dd>{decision.policy_section}</dd>
        <dt>Payment</dt>
        <dd>{paymentText(claim)}</dd>
        {claim.sign_off && (
          <>
            <dt>Signed off by</dt>
            <dd>{claim.sign_off.handler_name}</dd>
          </>
        )}
      </dl>
      <p className="reason">{decision.reason}</p>
    </section>
  );
}

function PolicyPanel({ policyId }: Readonly<{ policyId: string }>) {
  const load = useCallback(() => api.getPolicy(policyId), [policyId]);
  const { data: policy } = usePolled<Policy>(load, never);
  if (!policy) return null;
  return (
    <section className="panel">
      <h2>Policy</h2>
      <dl className="facts">
        <dt>Policy</dt>
        <dd className="id">{policy.policy_id}</dd>
        <dt>Plan</dt>
        <dd>{label(policy.plan)}</dd>
        <dt>Add-ons</dt>
        <dd>{policy.add_ons.map(label).join(", ") || "None"}</dd>
        <dt>Bought</dt>
        <dd>{policy.purchased_on}</dd>
        <dt>Trip</dt>
        <dd>
          {policy.trip.destination}, {policy.trip.departs_on} to{" "}
          {policy.trip.returns_on}
        </dd>
        <dt>Trip cost</dt>
        <dd className="number">{money(policy.trip.trip_cost)}</dd>
        <dt>Travelers</dt>
        <dd>{policy.travelers.join(", ")}</dd>
      </dl>
    </section>
  );
}

function HistoryPanel({ customerId }: Readonly<{ customerId: string }>) {
  const load = useCallback(() => api.getClaimHistory(customerId), [customerId]);
  const { data: history } = usePolled<PreviousClaim[]>(load, never);
  if (!history) return null;
  return (
    <section className="panel">
      <h2>Claim history</h2>
      {history.length === 0 ? (
        <p className="muted">No earlier claims.</p>
      ) : (
        <ul className="history">
          {history.map((claim) => (
            <li key={claim.claim_id}>
              <span className="id">{claim.claim_id}</span> {claim.filed_on}:{" "}
              {claim.summary}. {label(claim.outcome)},{" "}
              <span className="number">{money(claim.amount_paid)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function ClaimPage({ claimId }: Readonly<{ claimId: string }>) {
  const load = useCallback(
    async (): Promise<Loaded> => ({
      claim: await api.getClaim(claimId),
      steps: await api.listSteps(claimId),
    }),
    [claimId],
  );
  const { data, error, reload } = usePolled(load, agentWorking);

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p>Loading {claimId}</p>;
  const { claim, steps } = data;

  return (
    <>
      <p>
        <a href="#/">Back to the queue</a>
      </p>
      <div className="title">
        <h1>
          <span className="id">{claim.claim_id}</span> {claim.summary}
        </h1>
        <StatusBadge status={claim.status} />
      </div>
      <p className="muted">
        {label(claim.claim_type)} for {claim.customer_name}, at{" "}
        {claim.incident_location} on {claim.incident_date}. Submitted{" "}
        {claim.submitted_on}.
      </p>
      <div className="columns">
        <div>
          {claim.status === "awaiting_sign_off" && (
            <SignOffPanel claim={claim} onSignedOff={reload} />
          )}
          <DecisionPanel claim={claim} />
          <Steps
            steps={steps}
            working={claim.status !== "waiting" && agentWorking(data)}
          />
          <section className="panel">
            <h2>The customer's story</h2>
            <blockquote>{claim.story}</blockquote>
          </section>
          <section className="panel">
            <h2>Items claimed</h2>
            <table>
              <tbody>
                {claim.items.map((item) => (
                  <tr key={item.description}>
                    <td>{item.description}</td>
                    <td>{label(item.category)}</td>
                    <td className="amount">{money(item.amount)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <th colSpan={2}>Total claimed</th>
                  <td className="amount">{money(claim.amount_claimed)}</td>
                </tr>
              </tfoot>
            </table>
          </section>
          <section className="panel">
            <h2>Documents</h2>
            {claim.documents.map((document) => (
              <article key={document.name} className="document">
                <h3>{document.name}</h3>
                <p>{document.content}</p>
              </article>
            ))}
          </section>
        </div>
        <div>
          <PolicyPanel policyId={claim.policy_id} />
          <HistoryPanel customerId={claim.customer_id} />
        </div>
      </div>
    </>
  );
}
