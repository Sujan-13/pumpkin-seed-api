from pydantic import BaseModel, Field

class SeedIn(BaseModel):
    Area: float = Field(ge=30_000, le=200_000, description="Pixels inside the seed")
    Perimeter: float = Field(ge=600, le=2_000, description="Length of the outline")
    Major_Axis_Length: float = Field(ge=250, le=900, description="Long axis of the fitted ellipse")
    Minor_Axis_Length: float = Field(ge=100, le=450, description="Short axis of the fitted ellipse")
    Convex_Area: float = Field(ge=30_000, le=180_000, description="Pixels inside the convex hull")
    Equiv_Diameter: float = Field(ge=150, le=500, description="Diameter of a circle with the same area")
    Eccentricity: float = Field(ge=0, le=1, description="0 is a circle, near 1 is very elongated")
    Solidity: float = Field(ge=0.8, le=1, description="Area / Convex_Area")
    Extent: float = Field(ge=0.3, le=0.9, description="Area / bounding-box area")
    Roundness: float = Field(ge=0.3, le=1, description="4 * pi * Area / Perimeter^2")
    Aspect_Ration: float = Field(ge=1, le=5, description="Major / Minor axis (spelling matches the dataset)")
    Compactness: float = Field(ge=0.3, le=1, description="Equiv_Diameter / Major_Axis_Length")
