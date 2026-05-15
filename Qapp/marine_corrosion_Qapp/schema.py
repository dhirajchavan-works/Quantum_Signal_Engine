"""
schema.py
---------
Strict structural contracts for the Marine Corrosion QApp.

Uses Pydantic v1-compatible BaseModel for data validation.
All fields are typed, bounded, and documented.

Install dependency:
    pip install pydantic>=1.10,<3
"""

from __future__ import annotations

from typing import Dict
from pydantic import BaseModel, Field, validator


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------

class CorrosionInput(BaseModel):
    """
    Environmental and material parameters fed into the quantum circuit.

    All values represent physical measurements taken from a marine
    environment monitoring station at the moment of assessment.
    """

    salinity: float = Field(
        ...,
        ge=0.0,
        le=50.0,
        description="Water salinity in parts per thousand (ppt). Typical seawater: 30–40 ppt.",
    )
    temperature_celsius: float = Field(
        ...,
        ge=-5.0,
        le=45.0,
        description="Water temperature in degrees Celsius.",
    )
    pH: float = Field(
        ...,
        ge=0.0,
        le=14.0,
        description="Water pH level. Neutral = 7.0; acidic < 7.0; basic > 7.0.",
    )
    material_oxidation_potential: float = Field(
        ...,
        ge=-2.0,
        le=2.0,
        description=(
            "Standard electrode potential of the hull material in volts (V). "
            "e.g., steel ≈ -0.44 V, aluminium ≈ -0.76 V."
        ),
    )
    dissolved_oxygen_mgl: float = Field(
        ...,
        ge=0.0,
        le=20.0,
        description="Dissolved oxygen concentration in mg/L. Higher values accelerate oxidation.",
    )
    current_density_mAcm2: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Applied cathodic protection current density in mA/cm².",
    )

    class Config:
        schema_extra = {
            "example": {
                "salinity": 35.2,
                "temperature_celsius": 18.5,
                "pH": 7.8,
                "material_oxidation_potential": 0.44,
                "dissolved_oxygen_mgl": 6.5,
                "current_density_mAcm2": 0.12,
            }
        }

    @validator("pH")
    def ph_must_be_physical(cls, v: float) -> float:  # noqa: N805
        if not (0.0 <= v <= 14.0):
            raise ValueError(f"pH={v} is outside the physical range [0, 14].")
        return v

    @validator("material_oxidation_potential")
    def oxidation_potential_range(cls, v: float) -> float:  # noqa: N805
        if not (-2.0 <= v <= 2.0):
            raise ValueError(
                f"material_oxidation_potential={v} is outside expected range [-2.0, 2.0] V."
            )
        return v

    def to_normalized(self) -> Dict[str, float]:
        """
        Normalize all fields to [0, π] for use as rotation gate angles.
        Each field is mapped linearly from its physical range into [0, π].
        """
        import math

        def norm(value: float, lo: float, hi: float) -> float:
            return math.pi * (value - lo) / (hi - lo)

        return {
            "theta_salinity": norm(self.salinity, 0.0, 50.0),
            "theta_temperature": norm(self.temperature_celsius, -5.0, 45.0),
            "theta_pH": norm(self.pH, 0.0, 14.0),
            "theta_oxidation": norm(self.material_oxidation_potential, -2.0, 2.0),
            "theta_oxygen": norm(self.dissolved_oxygen_mgl, 0.0, 20.0),
            "theta_current": norm(self.current_density_mAcm2, 0.0, 10.0),
        }


# ---------------------------------------------------------------------------
# Output Schema
# ---------------------------------------------------------------------------

class CorrosionOutput(BaseModel):
    """
    Corrosion Intelligence metrics derived from quantum execution results.

    These values are post-processed classical representations of
    quantum measurement distributions.
    """

    degradation_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Estimated probability that the hull material will exhibit significant "
            "corrosion degradation within the assessment window. Range: [0, 1]."
        ),
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Statistical confidence in the degradation_probability estimate, "
            "derived from shot distribution entropy. Range: [0, 1]."
        ),
    )
    recommended_anode_current: float = Field(
        ...,
        ge=0.0,
        description=(
            "Recommended sacrificial anode current in milliamps (mA) "
            "required to neutralise predicted corrosion rate."
        ),
    )
    dominant_state: str = Field(
        ...,
        description=(
            "The most frequently measured computational basis state (bit string). "
            "e.g., '101010'. Used for audit and reproducibility logging."
        ),
    )
    measurement_distribution: Dict[str, float] = Field(
        ...,
        description=(
            "Raw quantum shot distribution: mapping of basis state bit strings "
            "to their normalized frequency (probability). Sums to ~1.0."
        ),
    )
    shots_used: int = Field(
        ...,
        gt=0,
        description="Total number of simulator shots used to produce this result.",
    )

    class Config:
        schema_extra = {
            "example": {
                "degradation_probability": 0.347,
                "confidence_score": 0.821,
                "recommended_anode_current": 52.1,
                "dominant_state": "101010",
                "measurement_distribution": {"101010": 0.42, "010101": 0.31, "110011": 0.27},
                "shots_used": 4096,
            }
        }
