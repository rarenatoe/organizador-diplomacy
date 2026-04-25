import type { Mock } from "vitest";

/**
 * Wraps a successful payload in the Hey-API client response format.
 * Preserves full type safety for the `data` generic!
 */
export function mockApiSuccess<TData>(data: TData) {
  return {
    data,
    error: undefined,
    // Using native DOM objects satisfies the TypeScript interfaces completely
    request: new Request("http://localhost"),
    response: new Response(),
  };
}

/**
 * Wraps an error payload in the Hey-API client response format.
 */
export function mockApiError<TError>(error: TError, status = 400) {
  return {
    data: undefined,
    error,
    request: new Request("http://localhost"),
    response: new Response(null, { status, statusText: "Error" }),
  };
}

export function mockSdkSuccess(mockFn: Mock, data: unknown) {
  mockFn.mockResolvedValue({
    data,
    error: undefined,
    request: new Request("http://localhost"),
    response: new Response(),
  });
}

export function mockSdkError(mockFn: Mock, errorData: unknown) {
  mockFn.mockResolvedValue({
    data: undefined,
    error: errorData,
    request: new Request("http://localhost"),
    response: new Response(),
  });
}
