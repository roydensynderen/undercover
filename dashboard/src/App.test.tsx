import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { claim, claimRoutes, stubApi, summary } from "./stubs";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.location.hash = "";
});

it("shows the queue first", async () => {
  stubApi({ "GET /api/claims": [summary()] });
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "Claims queue" }),
  ).toBeDefined();
});

it("opens a claim from its link", async () => {
  stubApi({ "GET /api/claims": [summary()], ...claimRoutes(claim()) });
  render(<App />);
  await screen.findByRole("link", { name: "CLM-1001" });
  act(() => {
    window.location.hash = "#/claims/CLM-1001";
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
  expect(
    await screen.findByText("My flight home from Rome was canceled."),
  ).toBeDefined();
});
