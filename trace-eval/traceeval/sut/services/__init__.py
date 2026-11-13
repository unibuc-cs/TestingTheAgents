"""Deterministic application services behind the tools (the "real application" the agents operate).

The services hold the business rules of the ContentOps platform and read and change the in-memory ``State``;
the tool adapters in ``tools/`` are thin wrappers around them. A service refuses a request by raising one
of the ``ToolError`` subclasses in ``errors``, which the dispatcher turns into an error result for the
agent. The modules:

    state        the platform data (users, pages, assets, ...), the audit log, the logical clock and the
                 idempotency cache
    errors       the refusals a service can raise
    repository   pages, versions, SEO metadata, assets (with alt texts) and search
    workflow     review requests and approvals, publishing, scheduling and taking pages down
    links        link validation of a page
    seo          the SEO report of a page
    permissions  roles and the actions they allow
    governance   permission checks, consent, personal-data export, the audit log and human approvals
    translation  translation jobs
    brand        the brand guidelines and the check of a page against them
    site         page analytics and the site audit
"""
