import {
  formatDate,
  getCountryEmoji,
  translateCountry,
  translateField,
  translateValue,
} from "./i18n";

describe("translateCountry", () => {
  it("should translate English country names to Spanish", () => {
    expect(translateCountry("England")).toBe("Inglaterra");
    expect(translateCountry("France")).toBe("Francia");
    expect(translateCountry("Germany")).toBe("Alemania");
    expect(translateCountry("Italy")).toBe("Italia");
    expect(translateCountry("Austria")).toBe("Austria");
    expect(translateCountry("Russia")).toBe("Rusia");
    expect(translateCountry("Turkey")).toBe("Turquía");
  });

  it("should return the original name if no translation exists", () => {
    expect(translateCountry("Spain")).toBe("Spain");
    expect(translateCountry("Portugal")).toBe("Portugal");
    expect(translateCountry("Unknown")).toBe("Unknown");
  });

  it("should handle Spanish input (return as-is since already translated)", () => {
    expect(translateCountry("Inglaterra")).toBe("Inglaterra");
    expect(translateCountry("Francia")).toBe("Francia");
    expect(translateCountry("Alemania")).toBe("Alemania");
  });

  it("should be case sensitive", () => {
    expect(translateCountry("england")).toBe("england");
    expect(translateCountry("ENGLAND")).toBe("ENGLAND");
    expect(translateCountry("England")).toBe("Inglaterra");
  });
});

describe("getCountryEmoji", () => {
  it("should return emojis for English country names", () => {
    expect(getCountryEmoji("England")).toBe("🇬🇧");
    expect(getCountryEmoji("France")).toBe("🇫🇷");
    expect(getCountryEmoji("Germany")).toBe("🇩🇪");
    expect(getCountryEmoji("Italy")).toBe("🇮🇹");
    expect(getCountryEmoji("Austria")).toBe("🇦🇹");
    expect(getCountryEmoji("Russia")).toBe("🇷🇺");
    expect(getCountryEmoji("Turkey")).toBe("🇹🇷");
  });

  it("should return emojis for Spanish country names", () => {
    expect(getCountryEmoji("Inglaterra")).toBe("🇬🇧");
    expect(getCountryEmoji("Francia")).toBe("🇫🇷");
    expect(getCountryEmoji("Alemania")).toBe("🇩🇪");
    expect(getCountryEmoji("Italia")).toBe("🇮🇹");
    expect(getCountryEmoji("Rusia")).toBe("🇷🇺");
    expect(getCountryEmoji("Turquía")).toBe("🇹🇷");
  });

  it("should return empty string for unknown countries", () => {
    expect(getCountryEmoji("Spain")).toBe("");
    expect(getCountryEmoji("Portugal")).toBe("");
    expect(getCountryEmoji("Unknown")).toBe("");
  });

  it("should return empty string for null and undefined", () => {
    expect(getCountryEmoji(null)).toBe("");
    expect(getCountryEmoji(undefined)).toBe("");
  });

  it("should return empty string for empty string", () => {
    expect(getCountryEmoji("")).toBe("");
  });

  it("should be case sensitive", () => {
    expect(getCountryEmoji("england")).toBe("");
    expect(getCountryEmoji("ENGLAND")).toBe("");
    expect(getCountryEmoji("England")).toBe("🇬🇧");
  });
});

describe("formatDate", () => {
  it("should handle empty or null inputs", () => {
    expect(formatDate("")).toBe("");
    expect(formatDate(undefined)).toBe("");
  });

  it("should force naive backend timestamps to UTC by appending Z", () => {
    // Appending 'Z' causes the Date object to treat the string as UTC
    // rather than the user's local timezone.
    const naiveDate = "2026-04-25T23:02:47";
    const explicitUTCDate = "2026-04-25T23:02:47Z";

    const formattedNaive = formatDate(naiveDate);
    const formattedUTC = formatDate(explicitUTCDate);

    // Verify the parser successfully handled the string
    expect(formattedNaive).not.toContain("Invalid");
    // Verify both strings yield the exact same local time translation
    // Verify both strings yield the exact same local time translation
    expect(formattedNaive).toEqual(formattedUTC);
  });
});

describe("translateField", () => {
  it("translates known fields correctly", () => {
    expect(translateField("is_new")).toBe("Experiencia");
    expect(translateField("has_priority")).toBe("Prioridad");
    expect(translateField("juegos_este_ano")).toBe("Juegos");
  });

  it("returns the original field if unknown", () => {
    expect(translateField("unknown_field")).toBe("unknown_field");
  });
});

describe("translateValue", () => {
  it("translates is_new correctly", () => {
    expect(translateValue("is_new", true)).toBe("Nuevo");
    expect(translateValue("is_new", false)).toBe("Antiguo");
  });

  it("translates has_priority correctly", () => {
    expect(translateValue("has_priority", true)).toBe("Sí");
    expect(translateValue("has_priority", false)).toBe("No");
  });

  it("converts unknown fields to strings", () => {
    expect(translateValue("juegos_este_ano", 5)).toBe("5");
    expect(translateValue("unknown", null)).toBe("");
  });
});
