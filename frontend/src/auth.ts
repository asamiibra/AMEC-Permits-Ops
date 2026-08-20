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

export type BrowserAuthenticationState =
  | "READY"
  | "REDIRECTING";

const GUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

let msalClientPromise:
  | Promise<PublicClientApplication>
  | undefined;

let redirectHandlingPromise:
  | Promise<void>
  | undefined;


export function browserAuthMode(): BrowserAuthMode {
  const mode = (
    import.meta.env.MODE || ""
  )
    .trim()
    .toLowerCase();

  return (
    mode === "development"
    || mode === "test"
  )
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

  const apiScope =
    `api://${apiClientId}/access_as_user`;

  const configuration: Configuration = {
    auth: {
      clientId: webClientId,
      authority:
        `https://login.microsoftonline.com/${tenantId}`,
      redirectUri:
        window.location.origin,
      postLogoutRedirectUri:
        window.location.origin,
      navigateToLoginRequestUrl: true,
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

        await client.initialize();

        return client;
      }
    )();
  }

  return msalClientPromise;
}


function accountForTenant(
  client: PublicClientApplication,
  tenantId: string,
): AccountInfo | null {
  const normalizedTenantId =
    tenantId.toLowerCase();

  const active =
    client.getActiveAccount();

  if (
    active
    && active.tenantId.toLowerCase()
      === normalizedTenantId
  ) {
    return active;
  }

  const matchingAccounts =
    client
      .getAllAccounts()
      .filter(
        (account) => (
          account.tenantId.toLowerCase()
          === normalizedTenantId
        ),
      );

  if (matchingAccounts.length > 1) {
    throw new Error(
      "Multiple cached Entra accounts match the configured tenant",
    );
  }

  const account =
    matchingAccounts[0] || null;

  if (account) {
    client.setActiveAccount(
      account,
    );
  }

  return account;
}


async function handleRedirectOnce(
  client: PublicClientApplication,
  tenantId: string,
): Promise<void> {
  if (!redirectHandlingPromise) {
    redirectHandlingPromise = (
      async () => {
        const result =
          await client.handleRedirectPromise();

        if (!result?.account) {
          return;
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
      }
    )();
  }

  await redirectHandlingPromise;
}


export async function initializeBrowserAuthentication(): Promise<BrowserAuthenticationState> {
  if (
    browserAuthMode()
    === "DEV_HEADER"
  ) {
    return "READY";
  }

  const {
    tenantId,
    apiScope,
  } = entraConfiguration();

  const client =
    await initializedMsalClient();

  await handleRedirectOnce(
    client,
    tenantId,
  );

  const account =
    accountForTenant(
      client,
      tenantId,
    );

  if (account) {
    return "READY";
  }

  await client.loginRedirect({
    scopes: [
      apiScope,
    ],
  });

  return "REDIRECTING";
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

  const {
    tenantId,
    apiScope,
  } = entraConfiguration();

  const client =
    await initializedMsalClient();

  const account =
    accountForTenant(
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

      throw new Error(
        "Interactive Entra authentication redirect started",
      );
    }

    throw error;
  }
}
