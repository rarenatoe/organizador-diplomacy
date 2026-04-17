import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import CsvImportModal from "./CsvImportModal.svelte";

describe("CsvImportModal.svelte", () => {
  it("renders modal with correct title and description", () => {
    const onImport = vi.fn();
    const onCancel = vi.fn();

    render(CsvImportModal, {
      props: {
        onImport,
        onCancel,
      },
    });

    // Verify title and description are rendered
    expect(screen.getByText("Pegar CSV")).toBeTruthy();
    expect(
      screen.getByText(/Pega el contenido CSV con las columnas:/),
    ).toBeTruthy();
    expect(screen.getByText(/nombre, is_new/)).toBeTruthy();
  });

  it("autofocuses textarea on mount", () => {
    const onImport = vi.fn();
    const onCancel = vi.fn();

    render(CsvImportModal, {
      props: {
        onImport,
        onCancel,
      },
    });

    // Verify textarea is focused
    const textarea = screen.getByPlaceholderText(/nombre,is_new/);
    expect(document.activeElement).toBe(textarea);
  });

  it("calls onCancel when cancel button is clicked", async () => {
    const onImport = vi.fn();
    const onCancel = vi.fn();

    render(CsvImportModal, {
      props: {
        onImport,
        onCancel,
      },
    });

    // Click cancel button
    const cancelButton = screen.getByText("Cancelar");
    await fireEvent.click(cancelButton);

    // Verify onCancel was called
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("calls onCancel when overlay is clicked", async () => {
    const onImport = vi.fn();
    const onCancel = vi.fn();

    render(CsvImportModal, {
      props: {
        onImport,
        onCancel,
      },
    });

    // Click overlay (outside modal content)
    const titleElement = screen.getByText("Pegar CSV");
    const overlay = titleElement.closest(".modal-overlay") as HTMLElement;
    await fireEvent.click(overlay);

    // Verify onCancel was called
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("calls onImport with textarea content when import button is clicked", async () => {
    const onImport = vi.fn();
    const onCancel = vi.fn();

    render(CsvImportModal, {
      props: {
        onImport,
        onCancel,
      },
    });

    const testCsv =
      "nombre,is_new,juegos_este_ano,prioridad,partidas_deseadas,partidas_gm\nAlice,Nuevo,0,0,1,0";

    // Type in textarea
    const textarea = screen.getByPlaceholderText(/nombre,is_new/);
    await fireEvent.input(textarea, { target: { value: testCsv } });

    // Click import button
    const importButton = screen.getByText("Importar");
    await fireEvent.click(importButton);

    // Verify onImport was called with correct content
    expect(onImport).toHaveBeenCalledWith(testCsv);
  });

  it("clears textarea after successful import", async () => {
    const onImport = vi.fn();
    const onCancel = vi.fn();

    render(CsvImportModal, {
      props: {
        onImport,
        onCancel,
      },
    });

    const textarea = screen.getByPlaceholderText(/nombre,is_new/);
    const testCsv = "test,csv,content";

    // Type and import
    await fireEvent.input(textarea, { target: { value: testCsv } });
    await fireEvent.click(screen.getByText("Importar"));

    // Verify textarea is cleared after import
    expect((textarea as HTMLTextAreaElement).value).toBe("");
  });
});
