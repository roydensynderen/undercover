import { useEffect, useState } from "react";
import { api, type Claim, type Handler } from "./api";
import { money } from "./format";

export function SignOffPanel({
  claim,
  onSignedOff,
}: Readonly<{ claim: Claim; onSignedOff: () => void }>) {
  const [handlers, setHandlers] = useState<Handler[]>([]);
  const [handlerId, setHandlerId] = useState("");
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void api.listHandlers().then((all) => {
      const able = all.filter((handler) => handler.can_approve_over_limit);
      setHandlers(able);
      setHandlerId(able[0]?.handler_id ?? "");
    });
  }, []);

  const signOff = () => {
    setBusy(true);
    setError(undefined);
    api
      .signOff(claim.claim_id, handlerId)
      .then(onSignedOff, (reason: unknown) => {
        setError(reason instanceof Error ? reason.message : String(reason));
        setBusy(false);
      });
  };

  return (
    <section className="panel sign-off">
      <h2>Sign-off needed</h2>
      <p>
        The agent approved a payout of{" "}
        <span className="number">{money(claim.decision?.payout ?? 0)}</span>,
        which is over the approval limit. The payment waits until a handler
        signs off.
      </p>
      <div className="row">
        <label>
          Handler{" "}
          <select
            value={handlerId}
            onChange={(event) => {
              setHandlerId(event.target.value);
            }}
          >
            {handlers.map((handler) => (
              <option key={handler.handler_id} value={handler.handler_id}>
                {handler.name}, {handler.role}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={signOff}
          disabled={busy || handlerId === ""}
        >
          Sign off and pay
        </button>
      </div>
      {error && <p className="error">{error}</p>}
    </section>
  );
}
