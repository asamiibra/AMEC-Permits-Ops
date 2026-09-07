import {
  BrowserCacheLocation,
  InteractionRequiredAuthError,
  PublicClientApplication,
  type AccountInfo,
  type Configuration,
} from "@azure/msal-browser";

export type BrowserAuthMode =
  | "DEV_HEADER"
  | "ENTRA";

export type BrowserAuthStartupState =
  | "READY"
  | "REDIRECTING";

// Backward-compatible alias for the name used by the first Batch 2B draft.
export type BrowserAuthenticationState = BrowserAuthStartupState;

const GUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

let msalClientPromise:
  | Promise<PublicClientApplication>
  | undefined;

let redirectHandlingPromise:
  | Promise<AccountInfo | null>
  | undefined;

let startupState:
  | BrowserAuthStartupState
  | undefined;


export function browserAuthMode(): BrowserAuthMode {
  return import.meta.env.DEV
    ? "DEV_HEADER"
    : "ENTRA";
}


function requiredGuid(
  name: string,
  value: string | undefined,
): string {
  const normalized = (
    value || ""
  )
    .trim()
    .toLowerCase();

  if (!normalized) {
    throw new Error(
      `${name} is required for Entra authentication`,
    );
  }

  if (!GUID_PATTERN.test(normalized)) {
    throw new Error(
      `${name} must be a valid Entra GUID`,
    );
  }

  return normalized;
}


function entraConfiguration() {
  const tenantId = requiredGuid(
    "VITE_ENTRA_TENANT_ID",
    import.meta.env.VITE_ENTRA_TENANT_ID,
  );
  const webClientId = requiredGuid(
    "VITE_ENTRA_WEB_CLIENT_ID",
    import.meta.env.VITE_ENTRA_WEB_CLIENT_ID,
  );
  const apiClientId = requiredGuid(
    "VITE_ENTRA_API_CLIENT_ID",
    import.meta.env.VITE_ENTRA_API_CLIENT_ID,
  );

  if (webClientId === apiClientId) {
    throw new Error(
      "VITE_ENTRA_WEB_CLIENT_ID and VITE_ENTRA_API_CLIENT_ID must be different Entra application IDs",
    );
  }

  const apiScope =
    `api://${apiClientId}/access_as_user`;
  const redirectBridgeUri =
    `${window.location.origin}/redirect.html`;

  const configuration: Configuration = {
    auth: {
      clientId: webClientId,
      authority:
        `https://login.microsoftonline.com/${tenantId}`,
      // MSAL Browser v5 uses a dedicated same-origin redirect bridge for
      // redirect, popup, and hidden-iframe response handling under COOP.
      redirectUri:
        redirectBridgeUri,
      postLogoutRedirectUri:
        redirectBridgeUri,
    },
    cache: {
      cacheLocation:
        BrowserCacheLocation.SessionStorage,
    },
  };

  return {
    tenantId,
    apiScope,
    configuration,
  };
}


async function initializedMsalClient(): Promise<PublicClientApplication> {
  if (!msalClientPromise) {
    msalClientPromise = (
      async () => {
        const {
          configuration,
        } = entraConfiguration();

        const client =
          new PublicClientApplication(
            configuration,
          );

        // MSAL v3+ requires initialize() before any other MSAL API.
        await client.initialize();

        return client;
      }
    )();
  }

  return msalClientPromise;
}


function activeAccountForTenant(
  client: PublicClientApplication,
  tenantId: string,
): AccountInfo | null {
  const active =
    client.getActiveAccount();

  if (
    active
    && active.tenantId.toLowerCase()
      === tenantId.toLowerCase()
  ) {
    return active;
  }

  return null;
}


function matchingCachedAccounts(
  client: PublicClientApplication,
  tenantId: string,
): AccountInfo[] {
  const normalizedTenantId =
    tenantId.toLowerCase();

  return client
    .getAllAccounts()
    .filter(
      (account) => (
        account.tenantId.toLowerCase()
        === normalizedTenantId
      ),
    );
}


async function handleRedirectOnce(
  client: PublicClientApplication,
  tenantId: string,
): Promise<AccountInfo | null> {
  if (!redirectHandlingPromise) {
    redirectHandlingPromise = (
      async () => {
        // MSAL Browser v5 moved navigateToLoginRequestUrl from
        // Configuration.auth to HandleRedirectPromiseOptions.
        const result =
          await client.handleRedirectPromise({
            navigateToLoginRequestUrl: true,
          });

        if (!result?.account) {
          return null;
        }

        if (
          result.account.tenantId.toLowerCase()
          !== tenantId.toLowerCase()
        ) {
          throw new Error(
            "Entra redirect returned an account from an unexpected tenant",
          );
        }

        client.setActiveAccount(
          result.account,
        );

        return result.account;
      }
    )();
  }

  return redirectHandlingPromise;
}


export async function initializeBrowserAuthentication(): Promise<BrowserAuthStartupState> {
  if (
    browserAuthMode()
    === "DEV_HEADER"
  ) {
    startupState = "READY";
    return startupState;
  }

  const {
    tenantId,
    apiScope,
  } = entraConfiguration();

  const client =
    await initializedMsalClient();

  const redirectAccount =
    await handleRedirectOnce(
      client,
      tenantId,
    );

  if (redirectAccount) {
    startupState = "READY";
    return startupState;
  }

  const activeAccount =
    activeAccountForTenant(
      client,
      tenantId,
    );

  if (activeAccount) {
    startupState = "READY";
    return startupState;
  }

  const cachedAccounts =
    matchingCachedAccounts(
      client,
      tenantId,
    );

  if (cachedAccounts.length === 1) {
    client.setActiveAccount(
      cachedAccounts[0],
    );
    startupState = "READY";
    return startupState;
  }

  startupState = "REDIRECTING";

  await client.loginRedirect({
    scopes: [
      apiScope,
    ],
    ...(
      cachedAccounts.length > 1
        ? {
            prompt:
              "select_account" as const,
          }
        : {}
    ),
  });

  return startupState;
}


export async function getApiAccessToken(): Promise<string> {
  if (
    browserAuthMode()
    !== "ENTRA"
  ) {
    throw new Error(
      "Entra access tokens are unavailable in DEV_HEADER mode",
    );
  }

  if (startupState !== "READY") {
    throw new Error(
      "Browser authentication startup is not READY",
    );
  }

  const {
    tenantId,
    apiScope,
  } = entraConfiguration();

  const client =
    await initializedMsalClient();

  const account =
    activeAccountForTenant(
      client,
      tenantId,
    );

  if (!account) {
    throw new Error(
      "Authenticated Entra account is unavailable",
    );
  }

  try {
    const result =
      await client.acquireTokenSilent({
        account,
        scopes: [
          apiScope,
        ],
      });

    const accessToken =
      result.accessToken.trim();

    if (!accessToken) {
      throw new Error(
        "Entra returned an empty API access token",
      );
    }

    return accessToken;
  } catch (error) {
    if (
      error
      instanceof InteractionRequiredAuthError
    ) {
      await client.acquireTokenRedirect({
        account,
        scopes: [
          apiScope,
        ],
      });

      // Redirect APIs do not provide a usable token to the current request.
      // Keep the current API call fail-closed.
      throw new Error(
        "Interactive Entra authentication redirect started",
      );
    }

    throw error;
  }
}
