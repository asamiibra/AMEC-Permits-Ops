import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

const TENANT_ID =
  "b27ffe53-8d31-4735-a07a-faa50c336d97";
const WEB_CLIENT_ID =
  "11111111-2222-4333-8444-555555555555";
const API_CLIENT_ID =
  "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee";

const msal = vi.hoisted(
  () => {
    class InteractionRequiredAuthError
      extends Error {}

    const instance = {
      initialize: vi.fn(),
      handleRedirectPromise: vi.fn(),
      getActiveAccount: vi.fn(),
      getAllAccounts: vi.fn(),
      setActiveAccount: vi.fn(),
      loginRedirect: vi.fn(),
      acquireTokenSilent: vi.fn(),
      acquireTokenRedirect: vi.fn(),
    };

    const configurations: unknown[] = [];

    const PublicClientApplication =
      vi.fn(
        function PublicClientApplication(
          configuration: unknown,
        ) {
          configurations.push(
            configuration,
          );

          return instance;
        },
      );

    return {
      InteractionRequiredAuthError,
      PublicClientApplication,
      configurations,
      instance,
    };
  },
);

vi.mock(
  "@azure/msal-browser",
  () => ({
    BrowserCacheLocation: {
      SessionStorage:
        "sessionStorage",
    },
    InteractionRequiredAuthError:
      msal.InteractionRequiredAuthError,
    PublicClientApplication:
      msal.PublicClientApplication,
  }),
);

function account(
  tenantId = TENANT_ID,
) {
  return {
    tenantId,
    homeAccountId:
      "home-account-id",
    localAccountId:
      "local-account-id",
    environment:
      "login.microsoftonline.com",
    username:
      "owner@example.test",
    name:
      "Owner",
  };
}

function stubEntraEnvironment() {
  vi.stubEnv(
    "MODE",
    "production",
  );
  vi.stubEnv(
    "VITE_ENTRA_TENANT_ID",
    TENANT_ID,
  );
  vi.stubEnv(
    "VITE_ENTRA_WEB_CLIENT_ID",
    WEB_CLIENT_ID,
  );
  vi.stubEnv(
    "VITE_ENTRA_API_CLIENT_ID",
    API_CLIENT_ID,
  );
}

async function loadAuth() {
  vi.resetModules();
  return import(
    "../src/auth"
  );
}

beforeEach(() => {
  msal.configurations.length = 0;

  msal.PublicClientApplication
    .mockClear();

  msal.instance.initialize.mockReset();
  msal.instance.handleRedirectPromise.mockReset();
  msal.instance.getActiveAccount.mockReset();
  msal.instance.getAllAccounts.mockReset();
  msal.instance.setActiveAccount.mockReset();
  msal.instance.loginRedirect.mockReset();
  msal.instance.acquireTokenSilent.mockReset();
  msal.instance.acquireTokenRedirect.mockReset();

  msal.instance.initialize
    .mockResolvedValue(undefined);
  msal.instance.handleRedirectPromise
    .mockResolvedValue(null);
  msal.instance.getActiveAccount
    .mockReturnValue(null);
  msal.instance.getAllAccounts
    .mockReturnValue([]);
  msal.instance.loginRedirect
    .mockResolvedValue(undefined);
  msal.instance.acquireTokenRedirect
    .mockResolvedValue(undefined);
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.clearAllMocks();
  vi.resetModules();
});

describe(
  "browser authentication",
  () => {
    it(
      "uses DEV_HEADER only for development and test modes",
      async () => {
        vi.stubEnv(
          "MODE",
          "test",
        );
        const auth =
          await loadAuth();

        expect(
          auth.browserAuthMode(),
        ).toBe(
          "DEV_HEADER",
        );

        vi.stubEnv(
          "MODE",
          "production",
        );

        expect(
          auth.browserAuthMode(),
        ).toBe(
          "ENTRA",
        );
      },
    );

    it(
      "does not initialize MSAL in DEV_HEADER mode",
      async () => {
        vi.stubEnv(
          "MODE",
          "development",
        );
        const auth =
          await loadAuth();

        await expect(
          auth.initializeBrowserAuthentication(),
        ).resolves.toBe(
          "READY",
        );

        expect(
          msal.PublicClientApplication,
        ).not.toHaveBeenCalled();
      },
    );

    it(
      "fails closed when required Entra configuration is missing",
      async () => {
        stubEntraEnvironment();
        vi.stubEnv(
          "VITE_ENTRA_TENANT_ID",
          "",
        );
        const auth =
          await loadAuth();

        await expect(
          auth.initializeBrowserAuthentication(),
        ).rejects.toThrow(
          "VITE_ENTRA_TENANT_ID is required",
        );
      },
    );

    it(
      "fails closed when an Entra identifier is not a GUID",
      async () => {
        stubEntraEnvironment();
        vi.stubEnv(
          "VITE_ENTRA_WEB_CLIENT_ID",
          "not-a-guid",
        );
        const auth =
          await loadAuth();

        await expect(
          auth.initializeBrowserAuthentication(),
        ).rejects.toThrow(
          "VITE_ENTRA_WEB_CLIENT_ID must be a valid Entra GUID",
        );
      },
    );

    it(
      "builds a single-tenant MSAL client with session storage and the API scope",
      async () => {
        stubEntraEnvironment();
        const auth =
          await loadAuth();

        await expect(
          auth.initializeBrowserAuthentication(),
        ).resolves.toBe(
          "REDIRECTING",
        );

        expect(
          msal.instance.initialize,
        ).toHaveBeenCalledTimes(1);

        expect(
          msal.configurations[0],
        ).toEqual(
          expect.objectContaining({
            auth:
              expect.objectContaining({
                clientId:
                  WEB_CLIENT_ID,
                authority:
                  `https://login.microsoftonline.com/${TENANT_ID}`,
                redirectUri:
                  window.location.origin,
                postLogoutRedirectUri:
                  window.location.origin,
                navigateToLoginRequestUrl:
                  true,
              }),
            cache: {
              cacheLocation:
                "sessionStorage",
            },
          }),
        );

        expect(
          msal.instance.loginRedirect,
        ).toHaveBeenCalledWith({
          scopes: [
            `api://${API_CLIENT_ID}/access_as_user`,
          ],
        });
      },
    );

    it(
      "accepts a successful redirect only from the configured tenant",
      async () => {
        stubEntraEnvironment();
        const returnedAccount =
          account();

        msal.instance.handleRedirectPromise
          .mockResolvedValue({
            account:
              returnedAccount,
          });
        msal.instance.getActiveAccount
          .mockReturnValue(
            returnedAccount,
          );

        const auth =
          await loadAuth();

        await expect(
          auth.initializeBrowserAuthentication(),
        ).resolves.toBe(
          "READY",
        );

        expect(
          msal.instance.setActiveAccount,
        ).toHaveBeenCalledWith(
          returnedAccount,
        );
        expect(
          msal.instance.loginRedirect,
        ).not.toHaveBeenCalled();
      },
    );

    it(
      "rejects a redirect account from another tenant",
      async () => {
        stubEntraEnvironment();
        msal.instance.handleRedirectPromise
          .mockResolvedValue({
            account:
              account(
                "22222222-3333-4444-8555-666666666666",
              ),
          });

        const auth =
          await loadAuth();

        await expect(
          auth.initializeBrowserAuthentication(),
        ).rejects.toThrow(
          "unexpected tenant",
        );
      },
    );

    it(
      "reuses one cached account from the configured tenant",
      async () => {
        stubEntraEnvironment();
        const cached =
          account();

        msal.instance.getAllAccounts
          .mockReturnValue([
            cached,
          ]);

        const auth =
          await loadAuth();

        await expect(
          auth.initializeBrowserAuthentication(),
        ).resolves.toBe(
          "READY",
        );

        expect(
          msal.instance.setActiveAccount,
        ).toHaveBeenCalledWith(
          cached,
        );
      },
    );

    it(
      "fails closed instead of guessing between multiple cached tenant accounts",
      async () => {
        stubEntraEnvironment();
        msal.instance.getAllAccounts
          .mockReturnValue([
            account(),
            {
              ...account(),
              localAccountId:
                "second-local-account",
              homeAccountId:
                "second-home-account",
            },
          ]);

        const auth =
          await loadAuth();

        await expect(
          auth.initializeBrowserAuthentication(),
        ).rejects.toThrow(
          "Multiple cached Entra accounts",
        );
      },
    );

    it(
      "acquires and trims an API access token silently",
      async () => {
        stubEntraEnvironment();
        const active =
          account();

        msal.instance.getActiveAccount
          .mockReturnValue(
            active,
          );
        msal.instance.acquireTokenSilent
          .mockResolvedValue({
            accessToken:
              "  api-access-token  ",
          });

        const auth =
          await loadAuth();

        await expect(
          auth.getApiAccessToken(),
        ).resolves.toBe(
          "api-access-token",
        );

        expect(
          msal.instance.acquireTokenSilent,
        ).toHaveBeenCalledWith({
          account:
            active,
          scopes: [
            `api://${API_CLIENT_ID}/access_as_user`,
          ],
        });
      },
    );

    it(
      "rejects an empty token",
      async () => {
        stubEntraEnvironment();
        msal.instance.getActiveAccount
          .mockReturnValue(
            account(),
          );
        msal.instance.acquireTokenSilent
          .mockResolvedValue({
            accessToken:
              "   ",
          });

        const auth =
          await loadAuth();

        await expect(
          auth.getApiAccessToken(),
        ).rejects.toThrow(
          "empty API access token",
        );
      },
    );

    it(
      "starts an interactive redirect when silent acquisition requires interaction",
      async () => {
        stubEntraEnvironment();
        const active =
          account();

        msal.instance.getActiveAccount
          .mockReturnValue(
            active,
          );
        msal.instance.acquireTokenSilent
          .mockRejectedValue(
            new msal.InteractionRequiredAuthError(
              "interaction required",
            ),
          );

        const auth =
          await loadAuth();

        await expect(
          auth.getApiAccessToken(),
        ).rejects.toThrow(
          "Interactive Entra authentication redirect started",
        );

        expect(
          msal.instance.acquireTokenRedirect,
        ).toHaveBeenCalledWith({
          account:
            active,
          scopes: [
            `api://${API_CLIENT_ID}/access_as_user`,
          ],
        });
      },
    );

    it(
      "never exposes an Entra token API in DEV_HEADER mode",
      async () => {
        vi.stubEnv(
          "MODE",
          "test",
        );
        const auth =
          await loadAuth();

        await expect(
          auth.getApiAccessToken(),
        ).rejects.toThrow(
          "unavailable in DEV_HEADER mode",
        );
      },
    );
  },
);
