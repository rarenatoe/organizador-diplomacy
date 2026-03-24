/**
 * Shared utility functions for the frontend.
 */

/**
 * Escapes HTML special characters to prevent XSS.
 * Uses the browser's built-in HTML escaping via textContent.
 */
export function esc(s: string | null | undefined): string {
  const el = document.createElement("span");
  el.textContent = s ?? "";
  return el.innerHTML;
}

/**
 * Parses CSV text into an array of player objects.
 * Expected columns: nombre, experiencia, juegos_este_ano, prioridad, partidas_deseadas, partidas_gm
 * Missing columns use sensible defaults.
 */
export function parsePlayersCsv(csvText: string): Array<{
  nombre: string;
  experiencia: string;
  juegos_este_ano: number;
  prioridad: number;
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
  const prioridadIdx = header.indexOf("prioridad");
  const deseadasIdx = header.indexOf("partidas_deseadas");
  const gmIdx = header.indexOf("partidas_gm");

  const result: Array<{
    nombre: string;
    experiencia: string;
    juegos_este_ano: number;
    prioridad: number;
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
      experiencia:
        experienciaIdx >= 0 ? (cols[experienciaIdx] ?? "Nuevo") : "Nuevo",
      juegos_este_ano:
        juegosIdx >= 0 ? parseInt(cols[juegosIdx] ?? "0", 10) || 0 : 0,
      prioridad:
        prioridadIdx >= 0 ? parseInt(cols[prioridadIdx] ?? "0", 10) || 0 : 0,
      partidas_deseadas:
        deseadasIdx >= 0 ? parseInt(cols[deseadasIdx] ?? "1", 10) || 1 : 1,
      partidas_gm: gmIdx >= 0 ? parseInt(cols[gmIdx] ?? "0", 10) || 0 : 0,
    });
  }

  return result;
}
