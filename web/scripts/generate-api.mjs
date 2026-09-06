import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import openapiTS, { astToString } from "openapi-typescript";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const contractPath = resolve(webRoot, "..", "contracts", "openapi.json");
const outputPath = resolve(
  webRoot,
  "src",
  "lib",
  "api",
  "generated",
  "schema.d.ts",
);
const checkOnly = process.argv.includes("--check");

const ast = await openapiTS(pathToFileURL(contractPath));
const expected = astToString(ast);

if (checkOnly) {
  let actual;
  try {
    actual = await readFile(outputPath, "utf8");
  } catch {
    actual = undefined;
  }
  if (actual !== expected) {
    console.error(`Generated API types are stale: ${outputPath}`);
    process.exitCode = 1;
  } else {
    console.log(`Generated API types are current: ${outputPath}`);
  }
} else {
  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(outputPath, expected, "utf8");
  console.log(`Wrote generated API types: ${outputPath}`);
}
