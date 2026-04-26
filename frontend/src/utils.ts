/**
 * Shared utility functions for the frontend.
 */

import { ErrorMessage, HttpValidationError } from "./generated-api";

/**
 * Parses CSV text into an array of player objects.
 * Expected columns: nombre, is_new, juegos_este_ano, prioridad, partidas_deseadas, partidas_gm
 * Missing columns use sensible defaults.
 */
export function parsePlayersCsv(csvText: string): Array<{
  nombre: string;
  is_new: boolean;
  juegos_este_ano: number;
  has_priority: boolean;
  partidas_deseadas: number;
  partidas_gm: number;
}> {
  const lines = csvText.trim().split("\n");
  if (lines.length === 0) return [];

  const headerCols =
    lines[0]
      ?.toLowerCase()
      .split(",")
      .map((h) => h.trim()) ?? [];
  const nameIndex = headerCols.indexOf("nombre");
  const experienceIndex = headerCols.indexOf("experiencia");
  const gamesThisYearIndex = headerCols.indexOf("juegos_este_ano");
  const priorityIndex = headerCols.indexOf("prioridad");
  const desiredGamesIndex = headerCols.indexOf("partidas_deseadas");
  const gmGamesIndex = headerCols.indexOf("partidas_gm");

  return lines
    .slice(1)
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map((line) => {
      const cols = line.split(",").map((c) => c.trim());
      const name = nameIndex >= 0 ? (cols[nameIndex] ?? "") : (cols[0] ?? "");

      const experienceText = experienceIndex >= 0 ? cols[experienceIndex] : "";
      const isNew = experienceText
        ? ["nuevo", "new", "principiante", "novato", "novice"].includes(
            experienceText.toLowerCase(),
          )
        : true;

      const gamesThisYearText =
        gamesThisYearIndex >= 0 ? cols[gamesThisYearIndex] : "";
      const parsedGamesThisYear = parseInt(gamesThisYearText ?? "", 10);
      const gamesThisYear = !isNaN(parsedGamesThisYear)
        ? parsedGamesThisYear
        : 0;

      const priorityText = priorityIndex >= 0 ? cols[priorityIndex] : "";
      const hasPriority = priorityText
        ? parseInt(priorityText, 10) > 0 ||
          ["true", "t", "si", "yes"].includes(priorityText.toLowerCase())
        : false;

      const desiredGamesText =
        desiredGamesIndex >= 0 ? cols[desiredGamesIndex] : "";
      const parsedDesiredGames = parseInt(desiredGamesText ?? "", 10);
      const desiredGames = !isNaN(parsedDesiredGames) ? parsedDesiredGames : 1;

      const gmGamesText = gmGamesIndex >= 0 ? cols[gmGamesIndex] : "";
      const parsedGmGames = parseInt(gmGamesText ?? "", 10);
      const gmGames = !isNaN(parsedGmGames) ? parsedGmGames : 0;

      return {
        nombre: name,
        is_new: isNew,
        juegos_este_ano: gamesThisYear,
        has_priority: hasPriority,
        partidas_deseadas: desiredGames,
        partidas_gm: gmGames,
      };
    })
    .filter((row) => row.nombre.length > 0);
}

/**
 * Normalize a name for comparison: lowercase, strip, collapse whitespace.
 */
export function normalizeName(name: string): string {
  return name.toLowerCase().trim().replace(/\s+/g, " ");
}

/**
 * Extracts a safe string from any FastAPI error response
 */
export function parseApiError(
  error: HttpValidationError | ErrorMessage,
): string {
  // 1. Is it a FastAPI 400/500 custom string error?
  // TypeScript now KNOWS this is valid and autocomplete will work!
  if ("detail" in error && typeof error.detail === "string") {
    return error.detail;
  }

  // 2. Is it a strict 422 Validation Error?
  if ("detail" in error && Array.isArray(error.detail)) {
    return error.detail.map((err) => err.msg).join("; ");
  }

  // 3. Fallback for custom interceptors
  if (typeof error === "string") {
    return error;
  }

  return "Ocurrió un error inesperado";
}
