import { vi } from "vitest";
import type {
  Claim,
  ClaimSummary,
  Handler,
  Policy,
  PreviousClaim,
  Step,
} from "./api";

/** Replies to fetch from a table of "METHOD /path" routes that tests can change. */
export function stubApi(routes: Record<string, unknown>) {
  const fetchMock = vi.fn((input: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${input}`;
    const route = routes[key];
    if (route === undefined) {
      return Promise.resolve(
        Response.json({ detail: `No stub for ${key}` }, { status: 404 }),
      );
    }
    return Promise.resolve(
      route instanceof Response ? route.clone() : Response.json(route),
    );
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function summary(overrides: Partial<ClaimSummary> = {}): ClaimSummary {
  return {
    claim_id: "CLM-1001",
    claim_type: "trip_delay",
    summary: "Flight home canceled",
    customer_name: "Maya Patel",
    submitted_on: "2026-06-24",
    amount_claimed: 420,
    status: "waiting",
    decision: null,
    payout: null,
    ...overrides,
  };
}

export function claim(overrides: Partial<Claim> = {}): Claim {
  return {
    claim_id: "CLM-1001",
    policy_id: "POL-2001",
    customer_id: "CUS-3001",
    customer_name: "Maya Patel",
    claim_type: "trip_delay",
    submitted_on: "2026-06-24",
    incident_date: "2026-06-18",
    incident_location: "Rome, Italy",
    summary: "Flight home canceled",
    story: "My flight home from Rome was canceled.",
    items: [
      { description: "Airport hotel", category: "accommodation", amount: 245 },
      { description: "Taxis", category: "transport", amount: 175 },
    ],
    amount_claimed: 420,
    documents: [
      {
        name: "Cancellation notice",
        type: "carrier_report",
        content: "Flight MA 611 was canceled.",
      },
    ],
    status: "waiting",
    decision: null,
    sign_off: null,
    payment: null,
    ...overrides,
  };
}

export const policy: Policy = {
  policy_id: "POL-2001",
  customer_id: "CUS-3001",
  plan: "premium",
  add_ons: ["electronics_plus"],
  purchased_on: "2026-04-22",
  sold_through: "Meridian Air checkout",
  trip: {
    destination: "Rome, Italy",
    departs_on: "2026-06-10",
    returns_on: "2026-06-18",
    trip_cost: 3100,
  },
  travelers: ["Maya Patel"],
  status: "active",
};

export const history: PreviousClaim[] = [
  {
    claim_id: "CLM-0412",
    filed_on: "2024-08-19",
    incident_date: "2024-08-09",
    claim_type: "baggage_delay",
    summary: "Checked bag arrived 30 hours late",
    outcome: "approved",
    amount_paid: 140,
  },
];

export const handlers: Handler[] = [
  {
    handler_id: "HND-01",
    name: "Dana Whitfield",
    role: "Senior Claims Handler",
    can_approve_over_limit: true,
  },
  {
    handler_id: "HND-09",
    name: "Trainee",
    role: "Trainee",
    can_approve_over_limit: false,
  },
];

export const steps: Step[] = [
  {
    step_id: 1,
    kind: "tool_call",
    text: 'get_claim({"claim_id": "CLM-1001"})',
    at: "2026-11-24T09:57:01+00:00",
  },
  {
    step_id: 2,
    kind: "tool_result",
    text: 'get_claim: {"claim_id": "CLM-1001"}',
    at: "2026-11-24T09:57:02+00:00",
  },
  {
    step_id: 3,
    kind: "reply",
    text: "Approved, $420.00.",
    at: "2026-11-24T09:57:09+00:00",
  },
];

/** The routes a claim page needs, for the claim given. */
export function claimRoutes(current: Claim): Record<string, unknown> {
  return {
    [`GET /api/claims/${current.claim_id}`]: current,
    [`GET /api/claims/${current.claim_id}/steps`]: [],
    "GET /api/policies/POL-2001": policy,
    "GET /api/customers/CUS-3001/claims": history,
    "GET /api/handlers": handlers,
  };
}
