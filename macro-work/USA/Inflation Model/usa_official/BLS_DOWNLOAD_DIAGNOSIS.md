# BLS bulk download diagnosis

Checked 18 September 2026.

The bulk service is available, but the Python HTTP client is blocked by the BLS edge security service. A single GET to `https://download.bls.gov/pub/time.series/CU/cu.item` returned HTTP 403 with `Server: AkamaiGHost` and the BLS bot-policy denial page. The client identified itself as `python-requests/2.34.2`. The response was HTML, not CPI data; no Retry-After header was supplied. The exact security rule is not disclosed, so it is not established whether client identification, connection characteristics, IP reputation or another signal caused the rejection.

The normal in-app browser opened the official CPI bulk directory successfully. Clicking its `cu.item` link emitted a browser download event. This verifies that the browser can initiate the download; the browser tool did not expose a saved file path, so the downloaded bytes were not inspected. Do not describe this as a verified local file acquisition.

The official BLS public API worked for the previous workbook build, including all 400 series for 2017–2026 and the complete histories of seven rebased series. This is a separate supported access method, not a bulk-server fix.

BLS's [automated-retrieval policy](https://www.bls.gov/bls/blsterms.htm) allows it to block excessive activity and robots without owner contact information. The existing generic Python user-agent has no owner contact information; this is a possible policy issue, not a confirmed cause. There was no attempt to spoof browser headers, replay browser cookies, rotate addresses or defeat the security filter.

For an entirely direct-BLS dataset, use the normal browser to save the official national bulk files, or complete the earlier histories through the [BLS public API](https://www.bls.gov/developers/), within its documented limits. A registered API key raises those limits. Persistent scripted bulk-access problems can be reported using the contact link and incident reference in `raw/bulk_download_diagnostic.json`.

The delivered workbook has not been relabelled as entirely direct-BLS. Its remaining pre-2017 mirror provenance is still documented accurately.
