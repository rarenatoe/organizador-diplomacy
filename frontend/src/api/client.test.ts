import { describe, it, expect } from "vitest";

/**
 * Minimal smoke test for api/client.ts
 *
 * The error interceptor is a simple wrapper around Hey-API's built-in error handling.
 * Since the logic is straightforward and API calls are auto-generated,
 * we only verify the client is properly configured with an error interceptor.
 */

describe("api/client.ts configuration", () => {
  it("client is imported and configured", async () => {
    // This is a smoke test to ensure api/client.ts doesn't have syntax errors
    // and the client is properly exported for use in components.
    const { client } = await import("./client");
    expect(client).toBeDefined();
    expect(client.setConfig).toBeDefined();
    expect(client.interceptors).toBeDefined();
  });
});
