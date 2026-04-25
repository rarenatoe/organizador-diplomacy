import { render, screen } from "@testing-library/svelte";

import SectionTitle from "./SectionTitle.svelte";

describe("SectionTitle", () => {
  it("renders the provided title correctly", () => {
    render(SectionTitle, { props: { title: "Test Title" } });

    const titleElement = screen.getByText("Test Title");
    expect(titleElement).toBeInTheDocument();
    expect(titleElement).toHaveClass("section-title");
  });

  it("renders title and count when count prop is provided", () => {
    render(SectionTitle, { props: { title: "Jugadores", count: 12 } });

    const titleElement = screen.getByText("Jugadores (12)");
    expect(titleElement).toBeInTheDocument();
  });

  it("does not render parenthesis or count if count is omitted", () => {
    render(SectionTitle, { props: { title: "Test Title" } });

    const titleElement = screen.getByText("Test Title");
    expect(titleElement).toBeInTheDocument();

    // Ensure count and parenthesis are not present
    expect(screen.queryByText("(")).not.toBeInTheDocument();
    expect(screen.queryByText(")")).not.toBeInTheDocument();
  });

  it("correctly applies custom class and style props to the wrapping div", () => {
    render(SectionTitle, {
      props: {
        title: "Styled Title",
        class: "custom-class",
        style: "margin-bottom: 20px; color: red;",
      },
    });

    const titleElement = screen.getByText("Styled Title");
    expect(titleElement).toBeInTheDocument();
    expect(titleElement).toHaveClass("section-title", "custom-class");
  });
});
