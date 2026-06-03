import { ProjectNewChat } from "@/components/projects/project-new-chat";

// A new chat inside a project. Server page awaits params (Next 16) and hands the
// project id to the client window, which generates the client-side chat id.
export default async function ProjectNewChatPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ProjectNewChat projectId={id} />;
}
