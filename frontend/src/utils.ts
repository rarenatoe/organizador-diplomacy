/**
 * Shared utility functions for the frontend.
 */

import { HttpValidationError } from "./generated-api";

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

  // Parse header to find column indices
  const header =
    lines[0]
      ?.toLowerCase()
      .split(",")
      .map((h) => h.trim()) ?? [];
  const nombreIdx = header.indexOf("nombre");
  const experienciaIdx = header.indexOf("experiencia");
  const juegosIdx = header.indexOf("juegos_este_ano");
  const hasPriorityIdx = header.indexOf("prioridad");
  const deseadasIdx = header.indexOf("partidas_deseadas");
  const gmIdx = header.indexOf("partidas_gm");

  const result: Array<{
    nombre: string;
    is_new: boolean;
    juegos_este_ano: number;
    has_priority: boolean;
    partidas_deseadas: number;
    partidas_gm: number;
  }> = [];

  // Process data rows (skip header)
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i]?.trim();
    if (!line) continue; // Skip empty rows

    const cols = line.split(",").map((c) => c.trim());

    // Get nombre (required)
    const nombre = nombreIdx >= 0 ? (cols[nombreIdx] ?? "") : (cols[0] ?? "");
    if (!nombre) continue; // Skip rows without a name

    result.push({
      nombre,
      is_new:
        experienciaIdx >= 0 && cols[experienciaIdx]
          ? ["nuevo", "new", "principiante", "novato", "novice"].includes(
              cols[experienciaIdx].toLocaleLowerCase(),
            )
          : true,
      juegos_este_ano:
        juegosIdx >= 0 && cols[juegosIdx]
          ? parseInt(cols[juegosIdx], 10) || 0
          : 0,
      has_priority:
        hasPriorityIdx >= 0 && cols[hasPriorityIdx]
          ? parseInt(cols[hasPriorityIdx], 10) > 0 ||
            ["true", "t", "si", "yes"].includes(
              cols[hasPriorityIdx].toLowerCase(),
            )
          : false,
      partidas_deseadas:
        deseadasIdx >= 0 && cols[deseadasIdx]
          ? parseInt(cols[deseadasIdx], 10) || 1
          : 1,
      partidas_gm:
        gmIdx >= 0 && cols[gmIdx] ? parseInt(cols[gmIdx], 10) || 0 : 0,
    });
  }

  return result;
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
export function parseApiError(error: HttpValidationError): string {
  // 1. Catch FastAPI Validation Errors (422) where detail is an array
  if (error.detail) {
    // We can safely map over the array knowing it matches the ValidationError shape
    return error.detail.map((err: { msg: string }) => err.msg).join("; ");
  }

  return "Ocurrió un error inesperado";
}
