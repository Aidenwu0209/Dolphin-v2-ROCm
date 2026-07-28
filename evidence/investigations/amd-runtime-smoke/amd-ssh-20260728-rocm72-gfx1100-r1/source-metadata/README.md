# OmniDocBench selected-image download metadata

This directory preserves provenance metadata for the 48 images selected for
the 2026-07-28 AMD SSH investigation. Dataset images themselves are excluded.

- Dataset: `opendatalab/OmniDocBench`
- Revision recorded by every Hugging Face sidecar:
  `aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec`
- Image count: 48
- Total image bytes at verification time: 56,910,542
- Sidecar count: 48
- Sidecars whose etag matched the corresponding image SHA-256: 48/48
- Download timestamp range recorded by the sidecars:
  `1785204864.9759512` to `1785204870.7256699`

`IMAGE_SHA256SUMS` records the name and digest of every source image without
copying image content. `METADATA_SHA256SUMS` covers the preserved sidecars.
The SHA-256 digests of those two sorted checksum streams are:

- `IMAGE_SHA256SUMS`:
  `aef4f807ee6ca07252dfddc09c63cb41fa31c9c62550efc3844fd21f7ff4cbb5`
- `METADATA_SHA256SUMS`:
  `20517827b2c631e7c389f954d42569c3f047f76b8e942693cfb2ad52b2a2d2fd`

The 48-image selection is the union of the first nine canary pages, two
timeout pages, 19 severe-union pages, 10 research-report dual-column pages,
and the eight TEDS pages absent from the retained prediction archive.

The original download command was not retained, so this evidence proves the
local files' revision and content identity, not the exact command history.
