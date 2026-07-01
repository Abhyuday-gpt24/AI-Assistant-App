"""Curated retrieval-eval set for the Next.js documentation.

Ingest the Next.js docs first (one topic, e.g. `nextjs`):

    # grab the docs folder from https://github.com/vercel/next.js/tree/canary/docs
    python -m src.app.rag_pipeline.data_ingestion.offline_batch_ingestion \\
        --dir path/to/next.js/docs --topic nextjs

Each item:
  - query             : a realistic user question
  - expected_keywords : terms that SHOULD appear in a correct chunk (case-insensitive
                        substring). Drives the Keyword-match metric.
  - expected_source   : substring(s) expected in the retrieved chunk's `filename`
                        (the doc's path relative to --dir, e.g. ".../dynamic-routes/...").
                        A string or a list of acceptable substrings. Drives Source-match
                        and MRR.

The `expected_source` fragments are folder/file names from the Next.js docs tree;
if your local docs layout differs, adjust them to match your ingested `filename`s.
"""

NEXTJS_EVAL = [
    {
        "query": "How do I create a dynamic route segment in the App Router?",
        "expected_keywords": ["dynamic", "params", "slug", "segment"],
        "expected_source": "dynamic-routes",
    },
    {
        "query": "How do I build an API endpoint with Route Handlers?",
        "expected_keywords": ["route", "GET", "Request", "Response"],
        "expected_source": "route-handlers",
    },
    {
        "query": "How does middleware work and where does the middleware file go?",
        "expected_keywords": ["middleware", "request", "NextResponse"],
        "expected_source": "middleware",
    },
    {
        "query": "What are React Server Components in Next.js?",
        "expected_keywords": ["server", "component", "render"],
        # Next.js docs merge both into one page: 05-server-and-client-components.mdx
        "expected_source": "server-and-client-components",
    },
    {
        "query": "When should I use the 'use client' directive?",
        "expected_keywords": ["use client", "client", "component"],
        # The directive's own reference page: use-client.mdx
        "expected_source": "use-client",
    },
    {
        "query": "How do I fetch and cache data in a Server Component?",
        "expected_keywords": ["fetch", "cache", "async", "await"],
        "expected_source": ["data-fetching", "fetching", "caching"],
    },
    {
        "query": "How do I mutate data with Server Actions?",
        "expected_keywords": ["use server", "server action", "mutation", "form"],
        "expected_source": "server-actions",
    },
    {
        "query": "How do I optimize images with the next/image component?",
        "expected_keywords": ["image", "width", "height", "optimization"],
        "expected_source": "image",
    },
    {
        "query": "How do I navigate between pages with the Link component?",
        "expected_keywords": ["link", "href", "navigate"],
        "expected_source": "link",
    },
    {
        "query": "How do I programmatically navigate using the useRouter hook?",
        "expected_keywords": ["useRouter", "router", "push"],
        "expected_source": "use-router",
    },
    {
        "query": "How do I statically generate dynamic routes at build time?",
        "expected_keywords": ["generateStaticParams", "static", "params"],
        "expected_source": "generate-static-params",
    },
    {
        "query": "How do I show a loading state with loading.js and streaming?",
        "expected_keywords": ["loading", "Suspense", "streaming"],
        # Both loading.mdx and streaming.mdx legitimately answer this.
        "expected_source": ["loading", "streaming"],
    },
    {
        "query": "How do I set the page title and SEO metadata?",
        "expected_keywords": ["metadata", "title", "description"],
        "expected_source": "metadata",
    },
    {
        "query": "How do nested layouts work in the app directory?",
        "expected_keywords": ["layout", "nested", "children"],
        "expected_source": "layout",
    },
]
