# Tankan inflation expectations

Column M of `Data Inputs.xlsx`, sheet `JN`, contains the Bank of Japan Tankan's one-year-ahead outlook for general prices: all enterprises, all industries, average expected annual CPI inflation in per cent. The VAR uses this rate in levels, alongside unemployment and oil, for all national and Tokyo measures.

Source: https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=en&db=CO&code=TK99F0000204HCQ00000

The response is preserved in `tankan_expectations_source.json`. The retrieved series runs from 2014Q1 to 2026Q2; the latest expectation is 2.7%. This is the general-price outlook, not the output-price outlook or the Tankan business-conditions diffusion index.

For the monthly VAR, each quarter's reading becomes effective in the following month and is held until the next reading. Thus 2014Q1 first enters April 2014, and 2026Q2 enters July 2026. No interpolation or backward fill is applied. This is a conservative monthly timing convention, not an exact historical publication-calendar reconstruction. Earlier cells remain blank. Differencing the price indices after alignment starts estimation in May 2014.

To refresh, retrieve the same series, map each quarter to the following month, carry forward to the workbook's existing monthly dates, and replace column M. Preserve the original columns. Then run `jp.py`, regenerate Japan's charts, and rebuild the results dashboard. The browser can draw monthly conditional expectations paths, while the historical survey observations remain quarterly.

Unemployment in column I is the seasonally adjusted rate for both sexes from Japan's Labour Force Survey, stored in percentage points. Source: https://dashboard.e-stat.go.jp/api/1.0/Json/getData?Lang=EN&IndicatorCode=0301010000020020010&RegionCode=00000&Cycle=1&IsSeasonalAdjustment=2

This service uses the API feature of Statistics Dashboard, but the contents of this service are not guaranteed by the Statistics Bureau of Japan.
