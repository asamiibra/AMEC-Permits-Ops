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

type MockRedirectAccount = {
  tenantId: string;
  homeAccountId: string;
  localAccountId: string;
  environment: string;
  username: string;
  name: string;
};

type MockRedirectResult = {
  account: MockRedirectAccount;
} | null;


const msal = vi.hoisted(
  () => {
    class InteractionRequiredAuthError
      extends Error {}

    const callOrder: string[] = [];

    const instance = {
      initialize: vi.fn(
        async () => {
          callOrder.push(
            "initialize",
          );
        },
      ),
      handleRedirectPromise: vi.fn(
        async (): Promise<MockRedirectResult> => {
          callOrder.push(
            "handleRedirectPromise",
          );
          return null;
        },
      ),
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
      callOrder,
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
  suffix = "one",
) {
  return {
    tenantId,
    homeAccountId:
      `home-account-${suffix}`,
    localAccountId:
      `local-account-${suffix}`,
    environment:
      "login.microsoftonline.com",
    username:
      `${suffix}@example.test`,
    name:
      `Account ${suffix}`,
  };
}

function stubEntraEnvironment() {
  vi.stubEnv(
    "DEV",
    false,
  );
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

function stubDevelopmentEnvironment() {
  vi.stubEnv(
    "DEV",
    true,
  );
  vi.stubEnv(
    "MODE",
    "development",
  );
}

async function loadAuth() {
  vi.resetModules();
  return import(
    "../src/auth"
  );
}

beforeEach(() => {
  msal.callOrder.length = 0;
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
    .mockImplementation(
      async () => {
        msal.callOrder.push(
          "initialize",
        );
      },
    );
  msal.instance.handleRedirectPromise
    .mockImplementation(
      async () => {
        msal.callOrder.push(
          "handleRedirectPromise",
        );
        return null;
      },
    );
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
      "uses DEV_HEADER only when Vite DEV is true",
      async () => {
        stubDevelopmentEnvironment();
        const auth =
          await loadAuth();

        expect(
          auth.browserAuthMode(),
        ).toBe(
          "DEV_HEADER",
        );
      },
    );

    it(
      "uses ENTRA for MODE=test when Vite DEV is false",
      async () => {
        stubEntraEnvironment();
        vi.stubEnv(
          "MODE",
          "test",
        );
        const auth =
          await loadAuth();

        expect(
          auth.browserAuthMode(),
        ).toBe(
          "ENTRA",
        );
      },
    );

    it(
      "does not initialize MSAL or require Entra identifiers in DEV_HEADER mode",
      async () => {
        stubDevelopmentEnvironment();
        vi.stubEnv(
          "VITE_ENTRA_TENANT_ID",
          "",
        );
        vi.stubEnv(
          "VITE_ENTRA_WEB_CLIENT_ID",
          "",
        );
        vi.stubEnv(
          "VITE_ENTRA_API_CLIENT_ID",
          "",
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
      "fails closed when the tenant ID is missing",
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
      "fails closed when the web client ID is missing",
      async () => {
        stubEntraEnvironment();
        vi.stubEnv(
          "VITE_ENTRA_WEB_CLIENT_ID",
          "",
        );
        const auth =
          await loadAuth();

        await expect(
          auth.initializeBrowserAuthentication(),
        ).rejects.toThrow(
          "VITE_ENTRA_WEB_CLIENT_ID is required",
        );
      },
    );

    it(
      "fails closed when the API client ID is missing",
      async () => {
        stubEntraEnvironment();
        vi.stubEnv(
          "VITE_ENTRA_API_CLIENT_ID",
          "",
        );
        const auth =
          await loadAuth();

        await expect(
          auth.initializeBrowserAuthentication(),
        ).rejects.toThrow(
          "VITE_ENTRA_API_CLIENT_ID is required",
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
      "fails closed when the SPA and API client IDs are identical",
      async () => {
        stubEntraEnvironment();
        vi.stubEnv(
          "VITE_ENTRA_WEB_CLIENT_ID",
          API_CLIENT_ID,
        );
        const auth =
          await loadAuth();

        await expect(
          auth.initializeBrowserAuthentication(),
        ).rejects.toThrow(
          "must be different Entra application IDs",
        );

        expect(
          msal.PublicClientApplication,
        ).not.toHaveBeenCalled();
      },
    );

    it(
      "builds a single-tenant MSAL v5 client with the exact redirect bridge and API scope",
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
                  `${window.location.origin}/redirect.html`,
                postLogoutRedirectUri:
                  `${window.location.origin}/redirect.html`,
              }),
            cache: {
              cacheLocation:
                "sessionStorage",
            },
          }),
        );

        expect(
          msal.configurations[0],
        ).not.toEqual(
          expect.objectContaining({
            auth:
              expect.objectContaining({
                navigateToLoginRequestUrl:
                  expect.anything(),
              }),
          }),
        );

        expect(
          msal.configurations[0],
        ).not.toEqual(
          expect.objectContaining({
            cache:
              expect.objectContaining({
                storeAuthStateInCookie:
                  expect.anything(),
              }),
          }),
        );

        expect(
          msal.instance.handleRedirectPromise,
        ).toHaveBeenCalledWith({
          navigateToLoginRequestUrl:
            true,
        });

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
      "awaits initialize before redirect processing",
      async () => {
        stubEntraEnvironment();
        const auth =
          await loadAuth();

        await auth.initializeBrowserAuthentication();

        expect(
          msal.callOrder,
        ).toEqual([
          "initialize",
          "handleRedirectPromise",
        ]);
      },
    );

    it(
      "accepts a successful redirect only from the configured tenant",
      async () => {
        stubEntraEnvironment();
        const returnedAccount =
          account();

        msal.instance.handleRedirectPromise
          .mockImplementation(
            async () => {
              msal.callOrder.push(
                "handleRedirectPromise",
              );
              return {
                account:
                  returnedAccount,
              };
            },
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
          .mockImplementation(
            async () => {
              msal.callOrder.push(
                "handleRedirectPromise",
              );
              return {
                account:
                  account(
                    "22222222-3333-4444-8555-666666666666",
                  ),
              };
            },
          );

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
      "reuses an existing active account from the configured tenant",
      async () => {
        stubEntraEnvironment();
        const active =
          account();
        msal.instance.getActiveAccount
          .mockReturnValue(
            active,
          );

        const auth =
          await loadAuth();

        await expect(
          auth.initializeBrowserAuthentication(),
        ).resolves.toBe(
          "READY",
        );

        expect(
          msal.instance.loginRedirect,
        ).not.toHaveBeenCalled();
      },
    );

    it(
      "reuses exactly one cached account from the configured tenant",
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
        expect(
          msal.instance.loginRedirect,
        ).not.toHaveBeenCalled();
      },
    );

    it(
      "starts normal login when no eligible cached account exists",
      async () => {
        stubEntraEnvironment();
        msal.instance.getAllAccounts
          .mockReturnValue([
            account(
              "22222222-3333-4444-8555-666666666666",
              "other-tenant",
            ),
          ]);

        const auth =
          await loadAuth();

        await expect(
          auth.initializeBrowserAuthentication(),
        ).resolves.toBe(
          "REDIRECTING",
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
      "uses select_account when multiple eligible tenant accounts are cached",
      async () => {
        stubEntraEnvironment();
        msal.instance.getAllAccounts
          .mockReturnValue([
            account(
              TENANT_ID,
              "first",
            ),
            account(
              TENANT_ID,
              "second",
            ),
          ]);

        const auth =
          await loadAuth();

        await expect(
          auth.initializeBrowserAuthentication(),
        ).resolves.toBe(
          "REDIRECTING",
        );

        expect(
          msal.instance.setActiveAccount,
        ).not.toHaveBeenCalled();
        expect(
          msal.instance.loginRedirect,
        ).toHaveBeenCalledWith({
          scopes: [
            `api://${API_CLIENT_ID}/access_as_user`,
          ],
          prompt:
            "select_account",
        });
      },
    );

    it(
      "constructs exactly one MSAL client across startup and repeated API token calls",
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
              "api-access-token",
          });

        const auth =
          await loadAuth();

        await auth.initializeBrowserAuthentication();
        await auth.getApiAccessToken();
        await auth.getApiAccessToken();

        expect(
          msal.PublicClientApplication,
        ).toHaveBeenCalledTimes(1);
        expect(
          msal.instance.initialize,
        ).toHaveBeenCalledTimes(1);
        expect(
          msal.instance.handleRedirectPromise,
        ).toHaveBeenCalledTimes(1);
        expect(
          msal.instance.acquireTokenSilent,
        ).toHaveBeenCalledTimes(2);
      },
    );

    it(
      "fails closed if an API token is requested before startup is READY",
      async () => {
        stubEntraEnvironment();
        const auth =
          await loadAuth();

        await expect(
          auth.getApiAccessToken(),
        ).rejects.toThrow(
          "startup is not READY",
        );

        expect(
          msal.instance.acquireTokenSilent,
        ).not.toHaveBeenCalled();
      },
    );

    it(
      "acquires, trims, and returns the access token silently after READY startup",
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
            idToken:
              "must-not-be-used",
          });

        const auth =
          await loadAuth();
        await auth.initializeBrowserAuthentication();

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
      "rejects an empty access token",
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
              "   ",
          });

        const auth =
          await loadAuth();
        await auth.initializeBrowserAuthentication();

        await expect(
          auth.getApiAccessToken(),
        ).rejects.toThrow(
          "empty API access token",
        );
      },
    );

    it(
      "starts an interactive token redirect with the same account and scope when required",
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
        await auth.initializeBrowserAuthentication();

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
      "fails closed if READY state no longer has an active account",
      async () => {
        stubEntraEnvironment();
        const active =
          account();
        msal.instance.getActiveAccount
          .mockReturnValueOnce(
            active,
          )
          .mockReturnValueOnce(null);

        const auth =
          await loadAuth();
        await auth.initializeBrowserAuthentication();

        await expect(
          auth.getApiAccessToken(),
        ).rejects.toThrow(
          "Authenticated Entra account is unavailable",
        );
      },
    );

    it(
      "never exposes the Entra token API in DEV_HEADER mode",
      async () => {
        stubDevelopmentEnvironment();
        const auth =
          await loadAuth();
        await auth.initializeBrowserAuthentication();

        await expect(
          auth.getApiAccessToken(),
        ).rejects.toThrow(
          "unavailable in DEV_HEADER mode",
        );
      },
    );

    it(
      "does not manually persist access tokens",
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
              "api-access-token",
          });

        const sessionSpy =
          vi.spyOn(
            Storage.prototype,
            "setItem",
          );

        const auth =
          await loadAuth();
        await auth.initializeBrowserAuthentication();
        await auth.getApiAccessToken();

        expect(
          sessionSpy,
        ).not.toHaveBeenCalled();

        sessionSpy.mockRestore();
      },
    );
  },
);
