import fs from "node:fs/promises";
import path from "node:path";

const repoRoot = process.cwd();
const canonicalDir = path.join(repoRoot, "docs", "ai-rules");
const generatedHeader = ["", "", ""].join("\n");

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

  const sections: string[] = [generatedHeader.trimEnd()];

  for (const file of canonicalFiles) {
    const abs = path.join(canonicalDir, file);
    let raw = await fs.readFile(abs, "utf8");

    // Strip yaml frontmatter if it exists
    if (raw.startsWith("---\n") || raw.startsWith("---\r\n")) {
      const end = raw.indexOf("\n---", 3);
      if (end !== -1) {
        raw = raw.slice(end + 4).trimStart();
      }
    }
    sections.push(raw.trim());
  }

  const fullContent = sections.join("\n\n") + "\n";

  await writeFile(".clinerules", fullContent);
  await writeFile(".windsurfrules", fullContent);
  await writeFile(".github/copilot-instructions.md", fullContent);
}

main().catch((error: unknown) => {
  console.error(error);
  process.exit(1);
});
