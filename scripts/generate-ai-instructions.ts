import fs from "node:fs/promises";
import path from "node:path";
import { parse as parseYaml } from "yaml";

const repoRoot = process.cwd();
const canonicalDir = path.join(repoRoot, "docs", "ai-rules");
const generatedHeader = [
  "<!-- GENERATED FILE: DO NOT EDIT DIRECTLY -->",
  "<!-- Source of truth: docs/ai-rules/*.md -->",
  "",
].join("\n");

interface RuleMeta {
  id: string;
  title: string;
  scope: "project" | "language";
  priority: string;
  applyTo?: string[];
  outputs?: Record<string, string>;
  toolNotes?: Record<string, string>;
}

interface ParsedRule {
  filename: string;
  meta: RuleMeta;
  content: string;
  priority: number;
}

function parseFrontmatter(
  rawText: string,
  filePath: string,
): { meta: RuleMeta; content: string } {
  const normalized = rawText.replace(/\r\n/g, "\n");
  if (!normalized.startsWith("---\n")) {
    throw new Error(`Missing frontmatter in ${filePath}`);
  }
  const end = normalized.indexOf("\n---\n", 4);
  if (end === -1) {
    throw new Error(`Unterminated frontmatter in ${filePath}`);
  }
  const frontmatterText = normalized.slice(4, end);
  const content = normalized.slice(end + 5).trimStart();
  const data = parseYaml(frontmatterText) as RuleMeta;
  if (!data.id || !data.scope || !data.priority) {
    throw new Error(
      `Missing required frontmatter fields (id, scope, priority) in ${filePath}`,
    );
  }
  return { meta: data, content };
}

function renderCopilot(rule: ParsedRule): string {
  let body = rule.content.trim();

  if (rule.meta.id === "core") {
    body = body
      .replaceAll("`python.md`", "`python.instructions.md`")
      .replaceAll("`typescript.md`", "`typescript.instructions.md`");
  }

  if (rule.meta.scope === "language") {
    const applyTo = Array.isArray(rule.meta.applyTo) ? rule.meta.applyTo : [];
    const applyPattern =
      applyTo.length === 1 ? applyTo[0] : `{${applyTo.join(",")}}`;
    return `${generatedHeader}---\napplyTo: "${applyPattern}"\n---\n\n${body}\n`;
  }

  return `${generatedHeader}${body}\n`;
}

function renderTrae(rule: ParsedRule): string {
  const body = rule.content.trim();

  if (rule.meta.scope === "language") {
    const globs = Array.isArray(rule.meta.applyTo)
      ? rule.meta.applyTo.join(", ")
      : "";
    return `${generatedHeader}---\ndescription: ${rule.meta.title}\nglobs: ${globs}\n---\n\n${body}\n`;
  }

  return `${generatedHeader}---\ndescription: ${rule.meta.title}\n---\n\n${body}\n`;
}

function renderCline(rules: ParsedRule[]): string {
  const sections: string[] = [generatedHeader.trimEnd()];

  for (const rule of rules) {
    if (rule.meta.scope === "project") {
      sections.push(rule.content.trim());
    } else {
      const applyTo = Array.isArray(rule.meta.applyTo)
        ? rule.meta.applyTo.join(", ")
        : "";
      sections.push(
        `## ${rule.meta.title} (${applyTo})\n\n${rule.content.trim()}`,
      );
    }
  }

  return sections.join("\n\n") + "\n";
}

async function writeFile(
  relativePath: string,
  contents: string,
): Promise<void> {
  const absolute = path.join(repoRoot, relativePath);
  await fs.mkdir(path.dirname(absolute), { recursive: true });
  await fs.writeFile(absolute, contents, "utf8");
  process.stdout.write(`Wrote ${relativePath}\n`);
}

async function main(): Promise<void> {
  const files = await fs.readdir(canonicalDir);
  const canonicalFiles = files
    .filter((file) => file.endsWith(".md") && file !== "README.md")
    .sort();

  if (canonicalFiles.length === 0) {
    throw new Error("No canonical rules found in docs/ai-rules.");
  }

  const rules: ParsedRule[] = [];
  for (const file of canonicalFiles) {
    const abs = path.join(canonicalDir, file);
    const raw = await fs.readFile(abs, "utf8");
    const parsed = parseFrontmatter(raw, file);
    const priority = Number.parseInt(String(parsed.meta.priority || "0"), 10);
    rules.push({
      filename: file,
      meta: parsed.meta,
      content: parsed.content,
      priority,
    });
  }

  rules.sort((a, b) => {
    if (a.priority !== b.priority) {
      return b.priority - a.priority;
    }
    return String(a.meta.id).localeCompare(String(b.meta.id));
  });

  for (const rule of rules) {
    if (rule.meta.outputs?.copilot) {
      await writeFile(rule.meta.outputs.copilot, renderCopilot(rule));
    }
    if (rule.meta.outputs?.trae) {
      await writeFile(rule.meta.outputs.trae, renderTrae(rule));
    }
  }

  await writeFile(".clinerules", renderCline(rules));
}

main().catch((error: unknown) => {
  console.error(error);
  process.exit(1);
});
