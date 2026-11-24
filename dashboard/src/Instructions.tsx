import { api } from "./api";
import { usePolled } from "./usePolled";

const never = () => false;

export function Instructions() {
  const { data, error } = usePolled(api.getInstructions, never);

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p>Loading the instructions</p>;

  return (
    <>
      <h1>The agent's instructions</h1>
      <p className="muted">
        What the UnderCover Agent reads before it works each claim. Read only.
      </p>
      <section className="panel">
        <div className="instructions">{data.text}</div>
      </section>
    </>
  );
}
