"""
Calibration configuration for KMIA forecasting models.
This file centralizes blending weights and other empirical coefficients.
"""

# Blending weights for rules_model_v2
# Currently using scaffold values from research; these should be updated 
# once aggregate calibration metrics are finalized.
V2_CLIMATOLOGY_WEIGHT = 0.20
V2_FORECAST_WEIGHT = 0.70
V2_UNIFORM_WEIGHT = 0.10

# Blender configuration
# Current scaffold: 70% TWC, 30% NBM
BLENDER_TWC_WEIGHT = 0.70
BLENDER_NBM_WEIGHT = 0.30

# Validation thresholds
SUM_TO_ONE_TOLERANCE = 0.01
PROBABILITY_EPSILON = 1e-15
