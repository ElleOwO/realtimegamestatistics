import { rmSync } from "node:fs";
import { fileURLToPath } from "node:url";

// Next can retain an inconsistent app-path manifest after switching between
// `next dev` and mode-dependent production builds. Only remove the generated
// frontend cache; source files and dependencies are outside this path.
const buildDirectory = fileURLToPath(new URL("../.next", import.meta.url));
rmSync(buildDirectory, { recursive: true, force: true });
