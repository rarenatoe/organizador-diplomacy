import { client } from "../generated-api/client.gen";

// 1. Configure the Base URL
// Bracket notation is required by TypeScript for Vite's env index signatures
client.setConfig({ baseUrl: "" });

// 2. Add an Interceptor for Error Normalization
// Hey-API automatically parses the error JSON into the `error` argument.
// We use `unknown` and type-narrowing to satisfy strict ESLint rules.
client.interceptors.error.use((error: unknown, response: Response) => {
  let errorMessage = "An unexpected error occurred";

  if (error && typeof error === "object" && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;

    // Catch FastAPI Validation Errors (422)
    if (Array.isArray(detail)) {
      const messages = detail.map((e: unknown) => {
        if (e && typeof e === "object" && "msg" in e) {
          return String(e.msg);
        }
        return "Validation Error";
      });
      errorMessage = messages.join(", ");
    }
    // Catch standard FastAPI HTTPExceptions
    else if (typeof detail === "string") {
      errorMessage = detail;
    }
  } else if (response.statusText) {
    errorMessage = response.statusText;
  }

  // We return the normalized error object.
  // Hey-API will wrap this and return it as the `error` property to your components.
  return { error: errorMessage };
});

export { client };
