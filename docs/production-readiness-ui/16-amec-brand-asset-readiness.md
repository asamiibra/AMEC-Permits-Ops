# AMEC brand asset readiness

The supplied reference was inspected at 200×200 RGB with no alpha channel. No higher-quality official AMEC SVG, PDF, EPS, AI export, or transparent PNG was found in the repository.

The MVP uses the supplied artwork faithfully, cropped only to remove the unused outer white canvas and resampled with Lanczos into `frontend/public/brand/amec-logo-master.png` plus 1×/2×/3× derivatives. The full AMEC mark, English company name, and Arabic company name are preserved. The image is rendered in an intentional white logo surface because the supplied source is not transparently packaged.

The reusable `AmecLogo` component is the single rendering source. It uses responsive `srcSet`, intrinsic dimensions, `object-fit: contain`, no CSS filters, no RTL mirroring, and no compact crop.

Production dependency: `OFFICIAL_HIGH_RES_LOGO_REQUIRED_FROM_AMEC`. An official vector or high-resolution transparent PNG/PDF should replace the supplied-reference derivative before production branding is finalized.
