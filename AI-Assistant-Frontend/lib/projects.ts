// Projects are now live — the data + operations live in `lib/api/projects.ts`
// (typed client over the FastAPI `/api/projects` routes). This module is kept as
// a thin compatibility re-export; import from `@/lib/api/projects` for new code.
export type { Project, Project as ProjectSummary } from "@/lib/api/projects";
