import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { expect, it } from "vitest";

it("allows loopback dev origins so client islands can hydrate", () => {
  const configUrl = pathToFileURL(
    resolve(process.cwd(), "apps/web/next.config.mjs"),
  ).href;
  const output = execFileSync(
    process.execPath,
    [
      "--input-type=module",
      "--eval",
      `const { default: config } = await import(${JSON.stringify(configUrl)}); process.stdout.write(JSON.stringify(config.allowedDevOrigins ?? []));`,
    ],
    { encoding: "utf8" },
  );

  expect(JSON.parse(output)).toEqual(
    expect.arrayContaining(["127.0.0.1", "localhost"]),
  );
});
