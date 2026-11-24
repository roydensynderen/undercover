import { api, type ClaimSummary, type Status } from "./api";
import { finished, label, money, outcomeLabels, statusLabels } from "./format";
import { StatusBadge } from "./StatusBadge";
import { usePolled } from "./usePolled";

const STATUSES: Status[] = [
  "waiting",
  "in_progress",
  "awaiting_sign_off",
  "decided",
];

const anyOpen = (claims: ClaimSummary[]) =>
  claims.some((claim) => !finished(claim.status));

export function Queue() {
  const { data: claims, error } = usePolled(api.listClaims, anyOpen);

  if (error) return <p className="error">{error}</p>;
  if (!claims) return <p>Loading the queue</p>;

  return (
    <>
      <h1>Claims queue</h1>
      <ul className="counts" aria-label="Claims by state">
        {STATUSES.map((status) => (
          <li key={status} className={`count status-${status}`}>
            <span className="number">
              {claims.filter((claim) => claim.status === status).length}
            </span>
            {statusLabels[status]}
          </li>
        ))}
      </ul>
      <section className="panel">
        <table>
          <thead>
            <tr>
              <th>Claim</th>
              <th>Customer</th>
              <th>Type</th>
              <th>Summary</th>
              <th className="amount">Claimed</th>
              <th>State</th>
              <th>Decision</th>
              <th className="amount">Payout</th>
            </tr>
          </thead>
          <tbody>
            {claims.map((claim) => (
              <tr key={claim.claim_id}>
                <td>
                  <a className="id" href={`#/claims/${claim.claim_id}`}>
                    {claim.claim_id}
                  </a>
                </td>
                <td>{claim.customer_name}</td>
                <td>{label(claim.claim_type)}</td>
                <td>{claim.summary}</td>
                <td className="amount">{money(claim.amount_claimed)}</td>
                <td>
                  <StatusBadge status={claim.status} />
                </td>
                <td>{claim.decision ? outcomeLabels[claim.decision] : ""}</td>
                <td className="amount">
                  {claim.payout === null ? "" : money(claim.payout)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
