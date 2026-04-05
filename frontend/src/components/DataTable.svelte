<script lang="ts" module>
  import type { Snippet } from "svelte";

  export interface ColumnDef<T> {
    header: string;
    key?: keyof T;
    cell?: Snippet<[T, number]>;
    sticky?: boolean;
  }
</script>

<script lang="ts" generics="T">
  interface Props {
    data: T[];
    columns: ColumnDef<T>[];
  }

  let { data, columns }: Props = $props();
</script>

<div class="data-table-wrapper">
  <table class="data-table">
    <thead>
      <tr>
        {#each columns as col, i (i)}
          <th class:sticky-col={col.sticky}>{col.header}</th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each data as row, i (i)}
        <tr>
          {#each columns as col, j (j)}
            <td class:sticky-col={col.sticky}>
              {#if col.cell}
                {@render col.cell(row, i)}
              {:else if col.key}
                {row[col.key]}
              {/if}
            </td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .data-table-wrapper {
    flex: 1;
    overflow: auto;
    min-height: 0;
    margin: 0 18px 16px;
    border: 1px solid var(--border);
    border-radius: 8px;
    overscroll-behavior-y: none;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    min-width: max-content;
  }

  th {
    position: sticky;
    top: 0;
    z-index: 10;
    background: var(--surface2);
    padding: 7px 9px;
    text-align: left;
    font-weight: 600;
    font-size: 10px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.4px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    background-clip: padding-box;
    box-shadow: none;
  }

  td {
    padding: 6px 9px;
    border-bottom: 1px solid var(--border);
  }

  tr:last-child td {
    border-bottom: none;
  }

  tr:hover td {
    background: var(--surface2);
  }

  /* Dynamic Sticky Column Logic */
  .sticky-col {
    position: sticky;
    left: 0;
    z-index: 5;
    background: var(--surface);
    box-shadow: var(--shadow-sticky);
  }

  th.sticky-col {
    z-index: 12;
    background: var(--surface2);
  }

  tr:hover td.sticky-col {
    background: var(--surface2);
  }
</style>
