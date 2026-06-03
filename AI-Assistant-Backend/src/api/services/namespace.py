"""The one rule for RAG scoping: which Pinecone namespace a chat reads/writes.

- A **standalone** chat is isolated: its namespace IS its own `chat_id`, so it
  only ever retrieves the docs uploaded into it.
- A **project** chat SHARES its project's corpus: its namespace is the
  `project_id`, so every chat in the project reads/writes the same vectors.

This is the single source of truth for that decision — both the chat-stream path
and the ingestion path resolve the namespace through here so they can never drift.
"""


def resolve_rag_namespace(chat) -> str:
    """The Pinecone namespace for a persisted `Chat`: its project's id when the
    chat belongs to a project (shared corpus), else its own id (isolated)."""
    return chat.project_id or chat.id


def namespace_for(chat_id: str, project_id: str | None) -> str:
    """Same rule, for callers that only hold the raw ids (e.g. ingestion of a
    not-yet-persisted chat): the project namespace when there's a project, else
    the chat's own id."""
    return project_id or chat_id
