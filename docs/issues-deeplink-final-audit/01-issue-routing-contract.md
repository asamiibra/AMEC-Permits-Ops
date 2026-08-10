# Issue routing contract

One canonical issue maps to one existing resolution workspace. Route construction is centralized in the persona visibility projection and is reused by Issues, Work, and issue-focused destination pages.

Every visible link has an entity route, a persona-aware actionability result, a contextual CTA, and the `issue` focus query. No normal UI path uses `/issues/{id}` as a standalone page.

Focused project reads validate that the Finding belongs to the requested project and that its Permit application belongs to the same project. Mismatches return a structured 409.
