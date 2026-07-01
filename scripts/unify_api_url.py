import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

OLD_CONST = (
    "const apiBaseUrl =\n"
    "  process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "
    '"http://localhost:8000";\n'
)
IMPORT = 'import { getBackendApiUrl } from "@/lib/backend-api";\n\n'


def update_routes() -> None:
    for path in (ROOT / "apps/web/app/api").rglob("route.ts"):
        text = path.read_text(encoding="utf-8")
        if "getBackendApiUrl" in text:
            continue
        if "process.env.API_BASE_URL" not in text:
            continue
        text = text.replace(OLD_CONST, "")
        text = text.replace("apiBaseUrl", "getBackendApiUrl()")
        if not text.startswith("import { getBackendApiUrl"):
            text = IMPORT + text
        path.write_text(text, encoding="utf-8")
        print(f"route: {path.relative_to(ROOT)}")


def update_pages() -> None:
    pages = [
        "apps/web/app/[locale]/page.tsx",
        "apps/web/app/[locale]/portfolios/page.tsx",
        "apps/web/app/[locale]/reports/page.tsx",
        "apps/web/app/[locale]/reports/[reportId]/page.tsx",
        "apps/web/app/[locale]/instruments/[symbol]/page.tsx",
        "apps/web/app/[locale]/task-runs/page.tsx",
        "apps/web/app/[locale]/task-runs/[taskRunId]/page.tsx",
        "apps/web/app/[locale]/alerts/page.tsx",
    ]
    for rel in pages:
        path = ROOT / rel
        text = path.read_text(encoding="utf-8")
        text = re.sub(
            r'const apiBaseUrl = process\.env\.NEXT_PUBLIC_API_BASE_URL \?\? "http://localhost:8000";\n\n',
            "",
            text,
        )
        if 'from "@/lib/backend-api"' not in text:
            last_import = text.rfind("import ")
            line_end = text.find("\n", last_import)
            text = (
                text[: line_end + 1]
                + 'import { backendFetch } from "@/lib/backend-api";\n'
                + text[line_end + 1 :]
            )
        text = re.sub(
            r"await fetch\(`\$\{apiBaseUrl\}([^`]+)`",
            r"await backendFetch(`\1`",
            text,
        )
        text = text.replace(
            "const response = await fetch(`${apiBaseUrl}${path}`",
            "const response = await backendFetch(path",
        )
        path.write_text(text, encoding="utf-8")
        print(f"page: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    update_routes()
    update_pages()
