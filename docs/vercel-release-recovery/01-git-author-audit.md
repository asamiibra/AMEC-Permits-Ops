# Git Author Audit

Provider discovery was performed with `gh auth status` and `gh api user`.

- Provider: GitHub
- Account login: `asamiibra`
- Account ID: `242797432`
- Provider-associated email source: GitHub account ID/login-derived no-reply address
- Selected local author email: `242797432+asamiibra@users.noreply.github.com`
- Candidate count recorded: `1`
- Full private email list: not written

The GitHub account API exposed the authenticated login and numeric account ID. GitHub’s account-associated no-reply format is therefore `242797432+asamiibra@users.noreply.github.com`; no guessed personal address was used. The GitHub email-list endpoint was unavailable to the current token because it lacks the `user` scope.

## Relevant release history

The current branch is based on `branch/owner-form-simple-dashboard`, while the historical release references are on `branch/ui-productionization`. The commits from the supplied historical pushed SHA through the current entry include the following classifications:

| Range/commit | Author email classification | Committer email classification | Release relevance |
|---|---|---|---|
| `37eaa4d` through `fc61974` | `INVALID_LOCALHOST_STYLE` | `INVALID_LOCALHOST_STYLE` | historical UI/repository changes; current branch source baseline |
| `fc619748dc390af58924378b02d54b59f360a54a` | `INVALID_LOCALHOST_STYLE` | `INVALID_LOCALHOST_STYLE` | current source/workbook tip |
| `b1b3cb95352a83d8171658ab33c6881098a79c39` | `VALID_PROVIDER_ASSOCIATED` | `VALID_PROVIDER_ASSOCIATED` | recovery entry baseline only |

Current local configuration after remediation:

```text
user.name=Ahmed Sami
user.email=242797432+asamiibra@users.noreply.github.com
```

No history rewrite was performed.
