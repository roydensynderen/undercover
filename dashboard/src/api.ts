export type Status =
  "waiting" | "in_progress" | "awaiting_sign_off" | "decided";
export type Outcome = "approve" | "decline" | "refer";
export type StepKind = "tool_call" | "tool_result" | "reply";

export interface ClaimSummary {
  claim_id: string;
  claim_type: string;
  summary: string;
  customer_name: string;
  submitted_on: string;
  amount_claimed: number;
  status: Status;
  decision: Outcome | null;
  payout: number | null;
}

export interface Item {
  description: string;
  category: string;
  amount: number;
}

export interface ClaimDocument {
  name: string;
  type: string;
  content: string;
}

export interface Decision {
  decision: Outcome;
  payout: number;
  reason: string;
  policy_section: string;
  decided_at: string;
}

export interface SignOff {
  handler_id: string;
  handler_name: string;
  signed_at: string;
}

export interface Payment {
  amount: number;
  paid_at: string;
}

export interface Claim {
  claim_id: string;
  policy_id: string;
  customer_id: string;
  customer_name: string;
  claim_type: string;
  submitted_on: string;
  incident_date: string;
  incident_location: string;
  summary: string;
  story: string;
  items: Item[];
  amount_claimed: number;
  documents: ClaimDocument[];
  status: Status;
  decision: Decision | null;
  sign_off: SignOff | null;
  payment: Payment | null;
}

export interface Policy {
  policy_id: string;
  customer_id: string;
  plan: string;
  add_ons: string[];
  purchased_on: string;
  sold_through: string;
  trip: {
    destination: string;
    departs_on: string;
    returns_on: string;
    trip_cost: number;
  };
  travelers: string[];
  status: string;
}

export interface PreviousClaim {
  claim_id: string;
  filed_on: string;
  incident_date: string;
  claim_type: string;
  summary: string;
  outcome: string;
  amount_paid: number;
}

export interface Handler {
  handler_id: string;
  name: string;
  role: string;
  can_approve_over_limit: boolean;
}

export interface Step {
  step_id: number;
  kind: StepKind;
  text: string;
  at: string;
}

async function read<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = (await response.json()) as { detail?: unknown };
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : `The request failed (${String(response.status)})`,
    );
  }
  return (await response.json()) as T;
}

async function get<T>(path: string): Promise<T> {
  return read<T>(await fetch(path));
}

async function post<T>(path: string, body: object): Promise<T> {
  return read<T>(
    await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export const api = {
  listClaims: () => get<ClaimSummary[]>("/api/claims"),
  getClaim: (id: string) => get<Claim>(`/api/claims/${id}`),
  listSteps: (id: string) => get<Step[]>(`/api/claims/${id}/steps`),
  getPolicy: (id: string) => get<Policy>(`/api/policies/${id}`),
  getClaimHistory: (id: string) =>
    get<PreviousClaim[]>(`/api/customers/${id}/claims`),
  listHandlers: () => get<Handler[]>("/api/handlers"),
  getInstructions: () => get<{ text: string }>("/api/instructions"),
  signOff: (id: string, handlerId: string) =>
    post<Claim>(`/api/claims/${id}/sign-off`, { handler_id: handlerId }),
};
