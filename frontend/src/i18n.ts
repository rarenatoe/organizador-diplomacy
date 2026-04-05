// Country translation and emoji utilities
// Internal variable names use English, but translation values remain in Spanish

// Country name translations from English to Spanish
/* eslint-disable @typescript-eslint/naming-convention */
const countryTranslations: Record<string, string> = {
  England: "Inglaterra",
  France: "Francia",
  Germany: "Alemania",
  Italy: "Italia",
  Austria: "Austria",
  Russia: "Rusia",
  Turkey: "Turquía",
};
/* eslint-enable @typescript-eslint/naming-convention */

// Country emoji mappings for both English and Spanish names
/* eslint-disable @typescript-eslint/naming-convention */
const countryEmojis: Record<string, string> = {
  // English names (from backend)
  England: "🇬🇧",
  France: "🇫🇷",
  Germany: "🇩🇪",
  Italy: "🇮🇹",
  Austria: "🇦🇹",
  Russia: "🇷🇺",
  Turkey: "🇹🇷",
  // Spanish names (for display)
  Inglaterra: "🇬🇧",
  Francia: "🇫🇷",
  Alemania: "🇩🇪",
  Italia: "🇮🇹",
  Rusia: "🇷🇺",
  Turquía: "🇹🇷",
};
/* eslint-enable @typescript-eslint/naming-convention */

/**
 * Translates a country name from English to Spanish
 * @param country - The country name to translate (typically in English from backend)
 * @returns The translated country name in Spanish, or the original name if no translation exists
 */
export function translateCountry(country: string): string {
  return countryTranslations[country] || country;
}

/**
 * Gets the emoji flag for a country name
 * @param country - The country name (can be English or Spanish, or null/undefined)
 * @returns The emoji flag for the country, or empty string if no match found or country is null/undefined
 */
export function getCountryEmoji(country: string | null | undefined): string {
  return country ? countryEmojis[country] || "" : "";
}

/**
 * Translates an action type to Spanish display name
 * @param action - The action type to translate
 * @returns The translated action name in Spanish, or the original action if no translation exists
 */
export function formatAction(action: string): string {
  switch (action) {
    case "manual_edit":
      return "Edición Manual";
    case "notion_sync":
      return "Sincronización Notion";
    case "creation":
      return "Creación";
    default:
      return action;
  }
}

/**
 * Formats a date string to Spanish locale format
 * @param dateString - The date string to format
 * @returns The formatted date string in Spanish locale
 */
export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString("es-PE", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
