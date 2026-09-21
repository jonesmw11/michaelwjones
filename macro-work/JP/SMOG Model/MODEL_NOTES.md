# Japanese SMOG equations

This documents the existing Japanese specification implemented by the copied Australian workflow. Let x be the output gap in log units, y log real GDP, y* potential log GDP, u unemployment in per cent, u* the NAIRU, pi annual core inflation, pi_e expectations, n annual labour-cost growth, and m the four-quarter import-price level change. D is zero through 2012Q4 and one from 2013Q1.

## Observation equations

GDP:

$$y_t = y_t^* + x_t + e_{1,t}.$$

Unemployment:

$$u_t = u_t^* + \lambda_3 x_t + \rho_1(u_{t-1}-u_{t-1}^*) + \rho_2(u_{t-2}-u_{t-2}^*) + e_{2,t}.$$

Inflation:

$$\pi_t = (1-\beta_1-\beta_2)D_t\pi_t^e + (1-\beta_1-\beta_2-\beta_3-\gamma)(1-D_t)\pi_t^e + \beta_1\pi_{t-1}+\beta_2\pi_{t-2}+\beta_3(1-D_t)\pi_{t-3}+\gamma(1-D_t)n_{t-1}+\psi m_{t-1}+\lambda_1 x_t+e_{3,t}.$$

Labour-cost growth:

$$n_t = (1-\beta_4)\pi_t^e + \beta_4\pi_{t-1} + L(u_{t-1}-u_{t-1}^*) + e_{4,t},\qquad L=8+\frac{1}{1+\exp(-\lambda_2)}.$$

The positive loading L between 8 and 9 is inherited from the existing Japanese model. The optimizer estimates lambda2, and the equation uses the transformed loading L.

## State equations

$$x_t = \phi_1x_{t-1}+\phi_2x_{t-2}+\eta_{5,t}.$$

$$y_t^* = y_{t-1}^*+g^*+\eta_{6,t}.$$

$$u_t^* = u_{t-1}^*+\eta_{7,t}.$$

The other five states retain the required lags. All disturbances are zero-mean Gaussian, independent across the specified shock components and time. Observation standard deviations are eps1 to eps4; state standard deviations are eps5 to eps7. Covariance matrices use their squares.

Initial state means come from boosted HP trends in the historical sample; initial covariance is zero, preserving the existing specification. Bounded L-BFGS-B maximizes the Kalman-filter log likelihood. Each callback records accepted coefficients and each quarter's likelihood contribution. The NAIRU noise floor and parameter bounds follow the Australian fitting approach, with additional bounds for Japan's extra coefficients.

## Fitted coefficients

Fit sample: 1995Q1–2022Q4. Values are from the bundled Python fit; rerunning generation replaces the JSON and CSVs, but does not automatically rewrite this document.

| Coefficient | Estimate |
| --- | ---: |
| `beta1` | 0.770746863 |
| `beta2` | -0.0910669461 |
| `beta3` | -0.0445319698 |
| `beta4` | 2.17660944 |
| `eps1` | 0.00648657917 |
| `eps2` | 1e-05 |
| `eps3` | 0.285607658 |
| `eps4` | 5.34919935 |
| `eps5` | 0.00817564647 |
| `eps6` | 0.00500748209 |
| `eps7` | 0.1129641 |
| `g_star` | 0.00167828193 |
| `gamma` | -0.0108150368 |
| `lambda1` | 17.8593181 |
| `lambda2` | 6.88464295 |
| `lambda3` | -4.01151449 |
| `phi1` | 1.21091394 |
| `phi2` | -0.319172459 |
| `psi` | 0.00289160888 |
| `rho1` | 1.30493978 |
| `rho2` | -0.482032839 |

Effective labour-gap loading L: **8.998977665**.

The reported output gap is 100x, an approximate percentage deviation from potential. The charted unemployment gap is u* minus u, the opposite sign of the unemployment-gap terms used inside the equations.

[Back to the model](README.md)
