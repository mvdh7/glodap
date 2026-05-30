# %%
import numpy as np

import glodap


gdf_full = glodap.atlantic()

# Assign cruise uncertainties (TEMPORARY)
# TODO: will need to import this from a file once it's available
cruises = gdf_full[["cruise"]].groupby("cruise").mean()
params = {
    "tco2": (3.0, 1.5),
    "talk": (2.5, 1.2),
}
for p, u in params.items():
    cruises[f"{p}_u_cruise"] = u[0]  # std of per-cruise noise
    cruises[f"{p}_u_sample"] = u[1]  # std of per-sample noise

# %% Let's simulate!
# This lives outside the function
params_all = {
    c.replace("_u_cruise", "")
    for c in cruises.columns
    if c.endswith("_u_cruise")
}

# These will be the function arguments
params = ["tco2", "talk"]
# subset = None
u_global = 0  # std of whole dataset noise
rng = None
n_reps = 30
gdf = gdf_full[gdf_full.depth > 6000]

# def monte_carlo():
if params is None:
    params = list(params_all)
elif isinstance(params, str):
    params = [params]
for p in params:
    if p not in params_all:
        raise Exception(f'"{p}" is not a valid parameter')
if rng is None:
    rng = np.random.default_rng()
with_noise = {}
for p in params:
    u_cruise = cruises.loc[gdf.cruise][f"{p}_u_cruise"].values
    noise_cruise = rng.normal(
        scale=u_cruise,
        size=(n_reps, len(u_cruise)),
    )
    u_sample = cruises.loc[gdf.cruise][f"{p}_u_sample"].values
    noise_sample = rng.normal(
        scale=u_sample,
        size=(n_reps, len(u_sample)),
    )
    with_noise[p] = gdf[p].values + noise_sample
    # TODO cast noise_cruise back to full size and add above
    # TODO calculate and add noise_global
print(with_noise)
