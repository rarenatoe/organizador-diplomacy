import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/svelte";
import { createRawSnippet } from "svelte";
import DataTable, { type ColumnDef } from "./DataTable.svelte";

interface TestRow {
  id: number;
  name: string;
  value: number;
  active: boolean;
}

describe("DataTable.svelte", () => {
  const testData: TestRow[] = [
    { id: 1, name: "Alice", value: 100, active: true },
    { id: 2, name: "Bob", value: 200, active: false },
    { id: 3, name: "Charlie", value: 300, active: true },
  ];

  it("renders headers from column config", () => {
    const columns: ColumnDef<TestRow>[] = [
      { header: "ID", key: "id" },
      { header: "Name", key: "name" },
      { header: "Value", key: "value" },
      { header: "Active", key: "active" },
    ];

    render(DataTable as typeof DataTable<TestRow>, {
      props: { data: testData, columns },
    });

    expect(screen.getByText("ID")).toBeInTheDocument();
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Value")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("renders data mapped via the key property", () => {
    const columns: ColumnDef<TestRow>[] = [
      { header: "ID", key: "id" },
      { header: "Name", key: "name" },
      { header: "Value", key: "value" },
    ];

    render(DataTable as typeof DataTable<TestRow>, {
      props: { data: testData, columns },
    });

    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("100")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText("200")).toBeInTheDocument();
  });

  it("applies sticky-col class when sticky: true", () => {
    const columns: ColumnDef<TestRow>[] = [
      { header: "ID", key: "id", sticky: true },
      { header: "Name", key: "name" },
      { header: "Value", key: "value", sticky: true },
    ];

    const { container } = render(DataTable as typeof DataTable<TestRow>, {
      props: { data: testData, columns },
    });

    // Check that sticky columns have the sticky-col class
    const stickyThs = container.querySelectorAll("th.sticky-col");
    const stickyTds = container.querySelectorAll("td.sticky-col");

    // Should have 2 sticky columns (ID and Value) × 3 rows = 6 sticky cells + 2 sticky headers
    expect(stickyThs).toHaveLength(2);
    expect(stickyTds).toHaveLength(6);

    // Check specific headers are sticky
    expect(stickyThs[0]).toHaveTextContent("ID");
    expect(stickyThs[1]).toHaveTextContent("Value");

    // Check that non-sticky columns don't have the class
    const nonStickyThs = container.querySelectorAll("th:not(.sticky-col)");
    expect(nonStickyThs).toHaveLength(1);
    expect(nonStickyThs[0]).toHaveTextContent("Name");
  });

  it("handles empty data gracefully", () => {
    const columns: ColumnDef<TestRow>[] = [
      { header: "ID", key: "id" },
      { header: "Name", key: "name" },
    ];

    render(DataTable as typeof DataTable<TestRow>, {
      props: { data: [], columns },
    });

    expect(screen.getByText("ID")).toBeInTheDocument();
    expect(screen.getByText("Name")).toBeInTheDocument();

    // Should have no data rows
    const dataRows = screen.queryAllByRole("row");
    // Header row + no data rows = 1 total row
    expect(dataRows).toHaveLength(1);
  });

  it("renders footerRow snippet as a direct child of tbody", () => {
    const columns: ColumnDef<TestRow>[] = [
      { header: "ID", key: "id" },
      { header: "Name", key: "name" },
      { header: "Value", key: "value" },
    ];

    // Programmatically forge a valid Svelte 5 snippet for the test
    const mockFooterSnippet = createRawSnippet(() => ({
      render: () =>
        `<tr data-testid="mock-footer-row"><td>Mock Footer</td></tr>`,
    }));

    const { container } = render(DataTable as typeof DataTable<TestRow>, {
      props: {
        data: testData,
        columns,
        footerRow: mockFooterSnippet,
      },
    });

    const tbody = container.querySelector("tbody");
    const footerRow = screen.getByTestId("mock-footer-row");

    // 1. Verify it actually rendered
    expect(footerRow).toBeInTheDocument();

    // 2. Verify it is structurally inside the <tbody>
    expect(footerRow.parentElement).toBe(tbody);

    // 3. Verify it was placed exactly at the bottom of the table
    expect(tbody?.lastElementChild).toBe(footerRow);
  });
});
