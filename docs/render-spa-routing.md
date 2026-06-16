# Render SPA Routing

The frontend uses React Router. On static hosts, direct requests such as
`/nabh?tab=evidence` must return the compiled `index.html` so the client router
can resolve the route.

The frontend build creates static fallback files for known top-level routes, such
as `dist/nabh/index.html`, so deployed deep links keep working even if the host
does not have a wildcard rewrite configured.

For Render Static Sites, also configure this rewrite in the Render Dashboard when
possible:

| Source | Destination | Action |
| --- | --- | --- |
| `/*` | `/index.html` | `Rewrite` |

Render documents this as the recommended rule for client-side routing frameworks.
