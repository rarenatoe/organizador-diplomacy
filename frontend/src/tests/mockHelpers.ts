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
