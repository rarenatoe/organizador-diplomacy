import { getCountryEmoji, translateCountry } from "./i18n";

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
