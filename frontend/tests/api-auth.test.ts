import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

const auth = vi.hoisted(
  () => ({
    browserAuthMode:
      vi.fn(),
    getApiAccessToken:
      vi.fn(),
  }),
);

vi.mock(
  "../src/auth",
  () => ({
    browserAuthMode:
      auth.browserAuthMode,
    getApiAccessToken:
      auth.getApiAccessToken,
  }),
);

import {
  api,
} from "../src/api";

function response(
  status = 200,
  body = '{"status":"ok"}',
) {
  return {
    ok:
      status >= 200
      && status < 300,
    status,
    headers: {
      get: (
        name: string,
      ) => (
        name.toLowerCase()
        === "content-type"
          ? "application/json"
          : null
      ),
    },
    text:
      async () => body,
  };
}

function requestHeaders(
  fetchMock: ReturnType<typeof vi.fn>,
): Headers {
  const init = (
    fetchMock.mock.calls[0]?.[1]
  ) as RequestInit | undefined;

  return new Headers(
    init?.headers,
  );
}

beforeEach(() => {
  auth.browserAuthMode
    .mockReset();
  auth.getApiAccessToken
    .mockReset();

  sessionStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
  sessionStorage.clear();
});

describe(
  "API authentication boundary",
  () => {
    it(
      "DEV_HEADER strips caller Authorization and owns X-Dev-Role",
      async () => {
        auth.browserAuthMode
          .mockReturnValue(
            "DEV_HEADER",
          );

        sessionStorage.setItem(
          "proposalops-role",
          "RESPONSIBLE_ENGINEER",
        );

        const fetchMock =
          vi.fn()
            .mockResolvedValue(
              response(),
            );

        vi.stubGlobal(
          "fetch",
          fetchMock,
        );

        await api(
          "/api/dashboard",
          {
            headers: {
              Authorization:
                "Bearer caller-token",
              "X-Dev-Role":
                "SYSTEM_ADMIN",
              "X-Custom":
                "kept",
            },
          },
        );

        const headers =
          requestHeaders(
            fetchMock,
          );

        expect(
          headers.get(
            "Authorization",
          ),
        ).toBeNull();
        expect(
          headers.get(
            "X-Dev-Role",
          ),
        ).toBe(
          "RESPONSIBLE_ENGINEER",
        );
        expect(
          headers.get(
            "X-Custom",
          ),
        ).toBe(
          "kept",
        );
        expect(
          auth.getApiAccessToken,
        ).not.toHaveBeenCalled();
      },
    );

    it(
      "ENTRA strips X-Dev-Role and replaces caller Authorization with the trusted token",
      async () => {
        auth.browserAuthMode
          .mockReturnValue(
            "ENTRA",
          );
        auth.getApiAccessToken
          .mockResolvedValue(
            "trusted-token",
          );

        const fetchMock =
          vi.fn()
            .mockResolvedValue(
              response(),
            );

        vi.stubGlobal(
          "fetch",
          fetchMock,
        );

        await api(
          "/api/dashboard",
          {
            headers: {
              Authorization:
                "Bearer caller-token",
              "X-Dev-Role":
                "SYSTEM_ADMIN",
            },
          },
        );

        const headers =
          requestHeaders(
            fetchMock,
          );

        expect(
          headers.get(
            "Authorization",
          ),
        ).toBe(
          "Bearer trusted-token",
        );
        expect(
          headers.get(
            "X-Dev-Role",
          ),
        ).toBeNull();
      },
    );

    it(
      "fails before fetch when ENTRA cannot provide a token",
      async () => {
        auth.browserAuthMode
          .mockReturnValue(
            "ENTRA",
          );
        auth.getApiAccessToken
          .mockResolvedValue(
            "   ",
          );

        const fetchMock =
          vi.fn();

        vi.stubGlobal(
          "fetch",
          fetchMock,
        );

        await expect(
          api(
            "/api/dashboard",
          ),
        ).rejects.toThrow(
          "Authenticated API token is unavailable",
        );

        expect(
          fetchMock,
        ).not.toHaveBeenCalled();
      },
    );

    it(
      "does not force Content-Type for FormData",
      async () => {
        auth.browserAuthMode
          .mockReturnValue(
            "ENTRA",
          );
        auth.getApiAccessToken
          .mockResolvedValue(
            "trusted-token",
          );

        const fetchMock =
          vi.fn()
            .mockResolvedValue(
              response(),
            );

        vi.stubGlobal(
          "fetch",
          fetchMock,
        );

        const form =
          new FormData();
        form.append(
          "file",
          "synthetic",
        );

        await api(
          "/api/upload",
          {
            method:
              "POST",
            body:
              form,
          },
        );

        const headers =
          requestHeaders(
            fetchMock,
          );

        expect(
          headers.get(
            "Content-Type",
          ),
        ).toBeNull();
        expect(
          headers.get(
            "Authorization",
          ),
        ).toBe(
          "Bearer trusted-token",
        );
      },
    );

    it(
      "defaults DEV_HEADER to SYSTEM_ADMIN when no demo role is selected",
      async () => {
        auth.browserAuthMode
          .mockReturnValue(
            "DEV_HEADER",
          );

        const fetchMock =
          vi.fn()
            .mockResolvedValue(
              response(),
            );

        vi.stubGlobal(
          "fetch",
          fetchMock,
        );

        await api(
          "/api/dashboard",
        );

        expect(
          requestHeaders(
            fetchMock,
          ).get(
            "X-Dev-Role",
          ),
        ).toBe(
          "SYSTEM_ADMIN",
        );
      },
    );
  },
);
