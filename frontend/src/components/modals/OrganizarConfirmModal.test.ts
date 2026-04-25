import { describe, expect, it, vi } from "vitest";

import { fireEvent, render, screen } from "@testing-library/svelte";

import OrganizarConfirmModal from "./OrganizarConfirmModal.svelte";

describe("OrganizarConfirmModal", () => {
  const defaultValidation = {
    isAllOnes: false,
    gmShortage: null,
    excludedPlayers: [],
  };

  it("does not render overlay when not visible", () => {
    const { container } = render(OrganizarConfirmModal, {
      props: {
        visible: false,
        validation: defaultValidation,
        onConfirm: () => {},
        onEdit: () => {},
        onCancel: () => {},
      },
    });
    expect(container.querySelector(".confirm-overlay")).toBeNull();
  });

  it("shows all ones warning when isAllOnes is true", () => {
    render(OrganizarConfirmModal, {
      props: {
        visible: true,
        validation: { ...defaultValidation, isAllOnes: true },
        onConfirm: () => {},
        onEdit: () => {},
        onCancel: () => {},
      },
    });
    expect(
      screen.getByText(/Todos los jugadores tienen 1 partida deseada/),
    ).toBeTruthy();
  });

  it("shows GM shortage warning with correct counts", () => {
    render(OrganizarConfirmModal, {
      props: {
        visible: true,
        validation: {
          ...defaultValidation,
          gmShortage: { required: 2, assigned: 1 },
        },
        onConfirm: () => {},
        onEdit: () => {},
        onCancel: () => {},
      },
    });
    expect(
      screen.getByText(
        /Faltan GMs: Se proyectan 2 partidas pero solo hay 1 GM\(s\) asignado\(s\)/,
      ),
    ).toBeTruthy();
  });

  it("lists excluded players by name", () => {
    render(OrganizarConfirmModal, {
      props: {
        visible: true,
        validation: {
          ...defaultValidation,
          excludedPlayers: ["Alice", "Bob", "Charlie"],
        },
        onConfirm: () => {},
        onEdit: () => {},
        onCancel: () => {},
      },
    });
    expect(screen.getByText("Alice")).toBeTruthy();
    expect(screen.getByText("Bob")).toBeTruthy();
    expect(screen.getByText("Charlie")).toBeTruthy();
  });

  it("truncates excluded players list when over 5", () => {
    render(OrganizarConfirmModal, {
      props: {
        visible: true,
        validation: {
          ...defaultValidation,
          excludedPlayers: ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"],
        },
        onConfirm: () => {},
        onEdit: () => {},
        onCancel: () => {},
      },
    });
    expect(screen.getByText("P1")).toBeTruthy();
    expect(screen.getByText("P5")).toBeTruthy();
    expect(screen.queryByText("P6")).toBeNull();
    expect(screen.getByText("+ 3 más")).toBeTruthy();
  });

  it("calls callbacks when buttons are clicked", async () => {
    const onConfirm = vi.fn();
    const onEdit = vi.fn();
    const onCancel = vi.fn();

    render(OrganizarConfirmModal, {
      props: {
        visible: true,
        validation: defaultValidation,
        onConfirm,
        onEdit,
        onCancel,
      },
    });

    await fireEvent.click(screen.getByText("Organizar de todos modos"));
    expect(onConfirm).toHaveBeenCalledTimes(1);

    await fireEvent.click(screen.getByText("Volver a Editar"));
    expect(onEdit).toHaveBeenCalledTimes(1);

    await fireEvent.click(screen.getByText("Cancelar"));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
