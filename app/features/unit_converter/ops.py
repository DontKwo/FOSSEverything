"""Unit converter operations with dimensional analysis and precision arithmetic."""
from __future__ import annotations

import contextlib
import math
import re
from typing import Any

import pint

_UREG_CACHE: pint.UnitRegistry | None = None
_EXPR_UREG_CACHE: pint.UnitRegistry | None = None


def get_ureg() -> pint.UnitRegistry:
    # Lazily initialize and return the standard UnitRegistry.
    global _UREG_CACHE
    if _UREG_CACHE is None:
        _UREG_CACHE = pint.UnitRegistry(autoconvert_offset_to_baseunit=False)
        with contextlib.suppress(ValueError, pint.errors.RedefinitionError):
            _UREG_CACHE.define("mpg = mile / gallon = MPG")
    return _UREG_CACHE


def get_expr_ureg() -> pint.UnitRegistry:
    # Lazily initialize and return the expression UnitRegistry.
    global _EXPR_UREG_CACHE
    if _EXPR_UREG_CACHE is None:
        _EXPR_UREG_CACHE = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
        with contextlib.suppress(ValueError, pint.errors.RedefinitionError):
            _EXPR_UREG_CACHE.define("mpg = mile / gallon = MPG")
    return _EXPR_UREG_CACHE


def __getattr__(name: str) -> Any:
    # Defer registry initialization when accessed via module attributes.
    if name == "UREG":
        return get_ureg()
    if name == "EXPR_UREG":
        return get_expr_ureg()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

CATEGORIES: list[dict[str, Any]] = [
    {
        "id": "length",
        "name": "Length",
        "description": "Distances and linear dimensions",
        "units": [
            {"id": "m", "label": "Meter", "symbol": "m", "expr": "meter"},
            {"id": "km", "label": "Kilometer", "symbol": "km", "expr": "kilometer"},
            {"id": "cm", "label": "Centimeter", "symbol": "cm", "expr": "centimeter"},
            {"id": "mm", "label": "Millimeter", "symbol": "mm", "expr": "millimeter"},
            {"id": "um", "label": "Micrometer", "symbol": "um", "expr": "micrometer"},
            {"id": "nm", "label": "Nanometer", "symbol": "nm", "expr": "nanometer"},
            {"id": "angstrom", "label": "Angstrom", "symbol": "\u00c5", "expr": "angstrom"},
            {"id": "in", "label": "Inch", "symbol": "in", "expr": "inch"},
            {"id": "ft", "label": "Foot", "symbol": "ft", "expr": "foot"},
            {"id": "yd", "label": "Yard", "symbol": "yd", "expr": "yard"},
            {"id": "mi", "label": "Mile", "symbol": "mi", "expr": "mile"},
            {"id": "nautical_mile", "label": "Nautical Mile", "symbol": "nmi", "expr": "nautical_mile"},
            {"id": "light_year", "label": "Light Year", "symbol": "ly", "expr": "light_year"},
            {"id": "parsec", "label": "Parsec", "symbol": "pc", "expr": "parsec"},
        ],
    },
    {
        "id": "area",
        "name": "Area",
        "description": "Surface areas and real estate plots",
        "units": [
            {"id": "m2", "label": "Square Meter", "symbol": "m\u00b2", "expr": "meter ** 2"},
            {"id": "km2", "label": "Square Kilometer", "symbol": "km\u00b2", "expr": "kilometer ** 2"},
            {"id": "cm2", "label": "Square Centimeter", "symbol": "cm\u00b2", "expr": "centimeter ** 2"},
            {"id": "mm2", "label": "Square Millimeter", "symbol": "mm\u00b2", "expr": "millimeter ** 2"},
            {"id": "ha", "label": "Hectare", "symbol": "ha", "expr": "hectare"},
            {"id": "acre", "label": "Acre", "symbol": "acre", "expr": "acre"},
            {"id": "in2", "label": "Square Inch", "symbol": "in\u00b2", "expr": "inch ** 2"},
            {"id": "ft2", "label": "Square Foot", "symbol": "ft\u00b2", "expr": "foot ** 2"},
            {"id": "yd2", "label": "Square Yard", "symbol": "yd\u00b2", "expr": "yard ** 2"},
            {"id": "mi2", "label": "Square Mile", "symbol": "mi\u00b2", "expr": "mile ** 2"},
        ],
    },
    {
        "id": "volume",
        "name": "Volume & Capacity",
        "description": "Fluid, gas, and solid space dimensions",
        "units": [
            {"id": "L", "label": "Liter", "symbol": "L", "expr": "liter"},
            {"id": "mL", "label": "Milliliter", "symbol": "mL", "expr": "milliliter"},
            {"id": "m3", "label": "Cubic Meter", "symbol": "m\u00b3", "expr": "meter ** 3"},
            {"id": "cm3", "label": "Cubic Centimeter", "symbol": "cm\u00b3", "expr": "centimeter ** 3"},
            {"id": "uL", "label": "Microliter", "symbol": "uL", "expr": "microliter"},
            {"id": "gal", "label": "Gallon (US)", "symbol": "gal", "expr": "gallon"},
            {"id": "qt", "label": "Quart (US)", "symbol": "qt", "expr": "quart"},
            {"id": "pt", "label": "Pint (US)", "symbol": "pt", "expr": "pint"},
            {"id": "cup", "label": "Cup (US)", "symbol": "cup", "expr": "cup"},
            {"id": "fl_oz", "label": "Fluid Ounce (US)", "symbol": "fl oz", "expr": "fluid_ounce"},
            {"id": "tbsp", "label": "Tablespoon (US)", "symbol": "tbsp", "expr": "tablespoon"},
            {"id": "tsp", "label": "Teaspoon (US)", "symbol": "tsp", "expr": "teaspoon"},
            {"id": "ft3", "label": "Cubic Foot", "symbol": "ft\u00b3", "expr": "foot ** 3"},
            {"id": "in3", "label": "Cubic Inch", "symbol": "in\u00b3", "expr": "inch ** 3"},
            {"id": "bbl", "label": "Oil Barrel (US)", "symbol": "bbl", "expr": "barrel"},
        ],
    },
    {
        "id": "mass",
        "name": "Mass & Weight",
        "description": "Quantities of matter and gravitational weights",
        "units": [
            {"id": "kg", "label": "Kilogram", "symbol": "kg", "expr": "kilogram"},
            {"id": "g", "label": "Gram", "symbol": "g", "expr": "gram"},
            {"id": "mg", "label": "Milligram", "symbol": "mg", "expr": "milligram"},
            {"id": "ug", "label": "Microgram", "symbol": "ug", "expr": "microgram"},
            {"id": "t", "label": "Metric Ton", "symbol": "t", "expr": "metric_ton"},
            {"id": "lb", "label": "Pound", "symbol": "lb", "expr": "pound"},
            {"id": "oz", "label": "Ounce", "symbol": "oz", "expr": "ounce"},
            {"id": "grain", "label": "Grain", "symbol": "gr", "expr": "grain"},
            {"id": "carat", "label": "Carat", "symbol": "ct", "expr": "carat"},
            {"id": "slug", "label": "Slug", "symbol": "slug", "expr": "slug"},
            {"id": "short_ton", "label": "Short Ton (US)", "symbol": "ton", "expr": "short_ton"},
            {"id": "long_ton", "label": "Long Ton (UK)", "symbol": "long ton", "expr": "long_ton"},
        ],
    },
    {
        "id": "time",
        "name": "Time",
        "description": "Temporal durations and intervals",
        "units": [
            {"id": "s", "label": "Second", "symbol": "s", "expr": "second"},
            {"id": "ms", "label": "Millisecond", "symbol": "ms", "expr": "millisecond"},
            {"id": "us", "label": "Microsecond", "symbol": "us", "expr": "microsecond"},
            {"id": "ns", "label": "Nanosecond", "symbol": "ns", "expr": "nanosecond"},
            {"id": "min", "label": "Minute", "symbol": "min", "expr": "minute"},
            {"id": "hr", "label": "Hour", "symbol": "hr", "expr": "hour"},
            {"id": "day", "label": "Day", "symbol": "d", "expr": "day"},
            {"id": "week", "label": "Week", "symbol": "wk", "expr": "week"},
            {"id": "month", "label": "Month (30 days)", "symbol": "mo", "expr": "month"},
            {"id": "year", "label": "Year (Julian)", "symbol": "yr", "expr": "year"},
        ],
    },
    {
        "id": "temperature",
        "name": "Temperature",
        "description": "Thermal scales and thermodynamic states",
        "units": [
            {"id": "degC", "label": "Celsius", "symbol": "\u00b0C", "expr": "degC"},
            {"id": "degF", "label": "Fahrenheit", "symbol": "\u00b0F", "expr": "degF"},
            {"id": "kelvin", "label": "Kelvin", "symbol": "K", "expr": "kelvin"},
            {"id": "degR", "label": "Rankine", "symbol": "\u00b0R", "expr": "degR"},
        ],
    },
    {
        "id": "speed",
        "name": "Speed & Velocity",
        "description": "Linear rates of motion",
        "units": [
            {"id": "m_s", "label": "Meters per Second", "symbol": "m/s", "expr": "meter / second"},
            {"id": "km_h", "label": "Kilometers per Hour", "symbol": "km/h", "expr": "kilometer / hour"},
            {"id": "mph", "label": "Miles per Hour", "symbol": "mph", "expr": "mile / hour"},
            {"id": "knot", "label": "Knot", "symbol": "kn", "expr": "knot"},
            {"id": "ft_s", "label": "Feet per Second", "symbol": "ft/s", "expr": "foot / second"},
            {"id": "c", "label": "Speed of Light", "symbol": "c", "expr": "speed_of_light"},
        ],
    },
    {
        "id": "acceleration",
        "name": "Acceleration",
        "description": "Rates of velocity change",
        "units": [
            {"id": "m_s2", "label": "Meters per Second Squared", "symbol": "m/s\u00b2", "expr": "meter / second ** 2"},
            {"id": "ft_s2", "label": "Feet per Second Squared", "symbol": "ft/s\u00b2", "expr": "foot / second ** 2"},
            {"id": "gravity", "label": "Standard Gravity", "symbol": "g", "expr": "standard_gravity"},
            {"id": "galileo", "label": "Galileo", "symbol": "Gal", "expr": "galileo"},
        ],
    },
    {
        "id": "force",
        "name": "Force",
        "description": "Mechanical forces and loads",
        "units": [
            {"id": "N", "label": "Newton", "symbol": "N", "expr": "newton"},
            {"id": "kN", "label": "Kilonewton", "symbol": "kN", "expr": "kilonewton"},
            {"id": "MN", "label": "Meganewton", "symbol": "MN", "expr": "meganewton"},
            {"id": "lbf", "label": "Pound-Force", "symbol": "lbf", "expr": "force_pound"},
            {"id": "kgf", "label": "Kilogram-Force", "symbol": "kgf", "expr": "force_kilogram"},
            {"id": "dyn", "label": "Dyne", "symbol": "dyn", "expr": "dyne"},
            {"id": "poundal", "label": "Poundal", "symbol": "pdl", "expr": "poundal"},
        ],
    },
    {
        "id": "pressure",
        "name": "Pressure & Mechanical Stress",
        "description": "Force per unit area and stress",
        "units": [
            {"id": "Pa", "label": "Pascal", "symbol": "Pa", "expr": "pascal"},
            {"id": "kPa", "label": "Kilopascal", "symbol": "kPa", "expr": "kilopascal"},
            {"id": "MPa", "label": "Megapascal", "symbol": "MPa", "expr": "megapascal"},
            {"id": "GPa", "label": "Gigapascal", "symbol": "GPa", "expr": "gigapascal"},
            {"id": "bar", "label": "Bar", "symbol": "bar", "expr": "bar"},
            {"id": "mbar", "label": "Millibar", "symbol": "mbar", "expr": "millibar"},
            {"id": "psi", "label": "Pounds per Square Inch", "symbol": "psi", "expr": "psi"},
            {"id": "ksi", "label": "Kilopounds per Square Inch", "symbol": "ksi", "expr": "ksi"},
            {"id": "atm", "label": "Standard Atmosphere", "symbol": "atm", "expr": "atmosphere"},
            {"id": "torr", "label": "Torr", "symbol": "Torr", "expr": "torr"},
            {"id": "mmHg", "label": "Millimeters of Mercury", "symbol": "mmHg", "expr": "millimeter_Hg"},
            {"id": "inHg", "label": "Inches of Mercury", "symbol": "inHg", "expr": "inch_Hg"},
        ],
    },
    {
        "id": "energy",
        "name": "Energy, Work & Heat",
        "description": "Thermal, kinetic, electrical, and chemical energy",
        "units": [
            {"id": "J", "label": "Joule", "symbol": "J", "expr": "joule"},
            {"id": "kJ", "label": "Kilojoule", "symbol": "kJ", "expr": "kilojoule"},
            {"id": "MJ", "label": "Megajoule", "symbol": "MJ", "expr": "megajoule"},
            {"id": "Wh", "label": "Watt-Hour", "symbol": "Wh", "expr": "watt_hour"},
            {"id": "kWh", "label": "Kilowatt-Hour", "symbol": "kWh", "expr": "kilowatt_hour"},
            {"id": "MWh", "label": "Megawatt-Hour", "symbol": "MWh", "expr": "megawatt_hour"},
            {"id": "cal", "label": "Calorie (Thermochemical)", "symbol": "cal", "expr": "calorie"},
            {"id": "kcal", "label": "Kilocalorie / Food Calorie", "symbol": "kcal", "expr": "kilocalorie"},
            {"id": "BTU", "label": "British Thermal Unit", "symbol": "BTU", "expr": "BTU"},
            {"id": "therm", "label": "Therm (US)", "symbol": "therm", "expr": "therm"},
            {"id": "eV", "label": "Electronvolt", "symbol": "eV", "expr": "electron_volt"},
            {"id": "keV", "label": "Kiloelectronvolt", "symbol": "keV", "expr": "kiloelectron_volt"},
            {"id": "MeV", "label": "Megaelectronvolt", "symbol": "MeV", "expr": "megaelectron_volt"},
            {"id": "ft_lbf", "label": "Foot-Pound", "symbol": "ft\u22c5lbf", "expr": "foot * force_pound"},
            {"id": "erg", "label": "Erg", "symbol": "erg", "expr": "erg"},
        ],
    },
    {
        "id": "power",
        "name": "Power",
        "description": "Rate of doing work or transferring energy",
        "units": [
            {"id": "W", "label": "Watt", "symbol": "W", "expr": "watt"},
            {"id": "kW", "label": "Kilowatt", "symbol": "kW", "expr": "kilowatt"},
            {"id": "MW", "label": "Megawatt", "symbol": "MW", "expr": "megawatt"},
            {"id": "GW", "label": "Gigawatt", "symbol": "GW", "expr": "gigawatt"},
            {"id": "hp", "label": "Mechanical Horsepower", "symbol": "hp", "expr": "horsepower"},
            {"id": "metric_hp", "label": "Metric Horsepower", "symbol": "PS", "expr": "metric_horsepower"},
            {"id": "BTU_hr", "label": "BTU per Hour", "symbol": "BTU/h", "expr": "BTU / hour"},
            {"id": "ton_ref", "label": "Ton of Refrigeration", "symbol": "TR", "expr": "refrigeration_ton"},
        ],
    },
    {
        "id": "torque",
        "name": "Torque & Moment",
        "description": "Rotational forces and couples",
        "units": [
            {"id": "N_m", "label": "Newton-Meter", "symbol": "N\u22c5m", "expr": "newton * meter"},
            {"id": "kN_m", "label": "Kilonewton-Meter", "symbol": "kN\u22c5m", "expr": "kilonewton * meter"},
            {"id": "lbf_ft", "label": "Foot-Pound", "symbol": "lbf\u22c5ft", "expr": "force_pound * foot"},
            {"id": "lbf_in", "label": "Inch-Pound", "symbol": "lbf\u22c5in", "expr": "force_pound * inch"},
            {"id": "kgf_m", "label": "Kilogram-Force Meter", "symbol": "kgf\u22c5m", "expr": "force_kilogram * meter"},
        ],
    },
    {
        "id": "angle",
        "name": "Plane & Solid Angle",
        "description": "Geometric rotation and spherical sectors",
        "units": [
            {"id": "deg", "label": "Degree", "symbol": "\u00b0", "expr": "degree"},
            {"id": "rad", "label": "Radian", "symbol": "rad", "expr": "radian"},
            {"id": "grad", "label": "Gradian", "symbol": "grad", "expr": "gradian"},
            {"id": "arcmin", "label": "Arcminute", "symbol": "'", "expr": "arcminute"},
            {"id": "arcsec", "label": "Arcsecond", "symbol": "\"", "expr": "arcsecond"},
            {"id": "turn", "label": "Turn / Revolution", "symbol": "tr", "expr": "turn"},
            {"id": "sr", "label": "Steradian", "symbol": "sr", "expr": "steradian"},
        ],
    },
    {
        "id": "frequency",
        "name": "Frequency & Angular Speed",
        "description": "Cyclic repetition rates",
        "units": [
            {"id": "Hz", "label": "Hertz", "symbol": "Hz", "expr": "hertz"},
            {"id": "kHz", "label": "Kilohertz", "symbol": "kHz", "expr": "kilohertz"},
            {"id": "MHz", "label": "Megahertz", "symbol": "MHz", "expr": "megahertz"},
            {"id": "GHz", "label": "Gigahertz", "symbol": "GHz", "expr": "gigahertz"},
            {"id": "THz", "label": "Terahertz", "symbol": "THz", "expr": "terahertz"},
            {"id": "rpm", "label": "Revolutions per Minute", "symbol": "RPM", "expr": "rpm"},
            {"id": "rad_s", "label": "Radians per Second", "symbol": "rad/s", "expr": "radian / second"},
        ],
    },
    {
        "id": "density",
        "name": "Density",
        "description": "Mass per unit volume",
        "units": [
            {"id": "kg_m3", "label": "Kilograms per Cubic Meter", "symbol": "kg/m\u00b3", "expr": "kilogram / meter ** 3"},
            {"id": "g_cm3", "label": "Grams per Cubic Centimeter", "symbol": "g/cm\u00b3", "expr": "gram / centimeter ** 3"},
            {"id": "g_mL", "label": "Grams per Milliliter", "symbol": "g/mL", "expr": "gram / milliliter"},
            {"id": "lb_ft3", "label": "Pounds per Cubic Foot", "symbol": "lb/ft\u00b3", "expr": "pound / foot ** 3"},
            {"id": "lb_in3", "label": "Pounds per Cubic Inch", "symbol": "lb/in\u00b3", "expr": "pound / inch ** 3"},
            {"id": "lb_gal", "label": "Pounds per Gallon (US)", "symbol": "lb/gal", "expr": "pound / gallon"},
        ],
    },
    {
        "id": "mass_flow",
        "name": "Mass Flow Rate",
        "description": "Rate of mass transit per unit time",
        "units": [
            {"id": "kg_s", "label": "Kilograms per Second", "symbol": "kg/s", "expr": "kilogram / second"},
            {"id": "kg_h", "label": "Kilograms per Hour", "symbol": "kg/h", "expr": "kilogram / hour"},
            {"id": "g_s", "label": "Grams per Second", "symbol": "g/s", "expr": "gram / second"},
            {"id": "lb_s", "label": "Pounds per Second", "symbol": "lb/s", "expr": "pound / second"},
            {"id": "lb_h", "label": "Pounds per Hour", "symbol": "lb/h", "expr": "pound / hour"},
            {"id": "t_h", "label": "Metric Tons per Hour", "symbol": "t/h", "expr": "metric_ton / hour"},
        ],
    },
    {
        "id": "volumetric_flow",
        "name": "Volumetric Flow Rate",
        "description": "Fluid and gas volume displacement rates",
        "units": [
            {"id": "m3_s", "label": "Cubic Meters per Second", "symbol": "m\u00b3/s", "expr": "meter ** 3 / second"},
            {"id": "m3_h", "label": "Cubic Meters per Hour", "symbol": "m\u00b3/h", "expr": "meter ** 3 / hour"},
            {"id": "L_s", "label": "Liters per Second", "symbol": "L/s", "expr": "liter / second"},
            {"id": "L_min", "label": "Liters per Minute", "symbol": "L/min", "expr": "liter / minute"},
            {"id": "gpm", "label": "Gallons per Minute (US)", "symbol": "GPM", "expr": "gallon / minute"},
            {"id": "cfm", "label": "Cubic Feet per Minute", "symbol": "CFM", "expr": "foot ** 3 / minute"},
            {"id": "bbl_day", "label": "Barrels per Day", "symbol": "bpd", "expr": "barrel / day"},
        ],
    },
    {
        "id": "dynamic_viscosity",
        "name": "Dynamic Viscosity",
        "description": "Fluid internal resistance to shear flow",
        "units": [
            {"id": "Pa_s", "label": "Pascal-Second", "symbol": "Pa\u22c5s", "expr": "pascal * second"},
            {"id": "mPa_s", "label": "Millipascal-Second", "symbol": "mPa\u22c5s", "expr": "millipascal * second"},
            {"id": "P", "label": "Poise", "symbol": "P", "expr": "poise"},
            {"id": "cP", "label": "Centipoise", "symbol": "cP", "expr": "centipoise"},
            {"id": "lbf_s_ft2", "label": "Pound-Force Second per Sq Foot", "symbol": "lbf\u22c5s/ft\u00b2", "expr": "force_pound * second / foot ** 2"},
        ],
    },
    {
        "id": "kinematic_viscosity",
        "name": "Kinematic Viscosity",
        "description": "Fluid momentum diffusivity",
        "units": [
            {"id": "m2_s", "label": "Square Meters per Second", "symbol": "m\u00b2/s", "expr": "meter ** 2 / second"},
            {"id": "mm2_s", "label": "Square Millimeters per Second", "symbol": "mm\u00b2/s", "expr": "millimeter ** 2 / second"},
            {"id": "St", "label": "Stokes", "symbol": "St", "expr": "stokes"},
            {"id": "cSt", "label": "Centistokes", "symbol": "cSt", "expr": "centistokes"},
            {"id": "ft2_s", "label": "Square Feet per Second", "symbol": "ft\u00b2/s", "expr": "foot ** 2 / second"},
        ],
    },
    {
        "id": "surface_tension",
        "name": "Surface Tension",
        "description": "Interfacial tension per unit length",
        "units": [
            {"id": "N_m", "label": "Newtons per Meter", "symbol": "N/m", "expr": "newton / meter"},
            {"id": "mN_m", "label": "Millinewtons per Meter", "symbol": "mN/m", "expr": "millinewton / meter"},
            {"id": "dyn_cm", "label": "Dynes per Centimeter", "symbol": "dyn/cm", "expr": "dyne / centimeter"},
            {"id": "lbf_in", "label": "Pound-Force per Inch", "symbol": "lbf/in", "expr": "force_pound / inch"},
        ],
    },
    {
        "id": "thermal_conductivity",
        "name": "Thermal Conductivity",
        "description": "Material thermal conduction coefficient",
        "units": [
            {"id": "W_m_K", "label": "Watts per Meter-Kelvin", "symbol": "W/(m\u22c5K)", "expr": "watt / (meter * kelvin)"},
            {"id": "BTU_hr_ft_F", "label": "BTU per Hour-Foot-DegF", "symbol": "BTU/(h\u22c5ft\u22c5\u00b0F)", "expr": "BTU / (hour * foot * delta_degF)"},
            {"id": "cal_s_cm_C", "label": "Calories per Sec-Centimeter-DegC", "symbol": "cal/(s\u22c5cm\u22c5\u00b0C)", "expr": "calorie / (second * centimeter * delta_degC)"},
        ],
    },
    {
        "id": "heat_transfer",
        "name": "Heat Transfer Coefficient",
        "description": "Convective thermal conductance per unit area",
        "units": [
            {"id": "W_m2_K", "label": "Watts per Sq Meter-Kelvin", "symbol": "W/(m\u00b2\u22c5K)", "expr": "watt / (meter ** 2 * kelvin)"},
            {"id": "BTU_hr_ft2_F", "label": "BTU per Hour-Sq Foot-DegF", "symbol": "BTU/(h\u22c5ft\u00b2\u22c5\u00b0F)", "expr": "BTU / (hour * foot ** 2 * delta_degF)"},
        ],
    },
    {
        "id": "specific_heat",
        "name": "Specific Heat Capacity",
        "description": "Heat storage capacity per unit mass",
        "units": [
            {"id": "J_kg_K", "label": "Joules per Kilogram-Kelvin", "symbol": "J/(kg\u22c5K)", "expr": "joule / (kilogram * kelvin)"},
            {"id": "kJ_kg_K", "label": "Kilojoules per Kilogram-Kelvin", "symbol": "kJ/(kg\u22c5K)", "expr": "kilojoule / (kilogram * kelvin)"},
            {"id": "BTU_lb_F", "label": "BTU per Pound-DegF", "symbol": "BTU/(lb\u22c5\u00b0F)", "expr": "BTU / (pound * delta_degF)"},
            {"id": "cal_g_C", "label": "Calories per Gram-DegC", "symbol": "cal/(g\u22c5\u00b0C)", "expr": "calorie / (gram * delta_degC)"},
        ],
    },
    {
        "id": "fuel_economy",
        "name": "Fuel Economy",
        "description": "Vehicle fuel efficiency and consumption",
        "units": [
            {"id": "mpg", "label": "Miles per Gallon (US)", "symbol": "mpg", "expr": "mpg"},
            {"id": "km_L", "label": "Kilometers per Liter", "symbol": "km/L", "expr": "kilometer / liter"},
            {"id": "L_100km", "label": "Liters per 100 km", "symbol": "L/100km", "expr": "L/100km"},
        ],
    },
    {
        "id": "digital_storage",
        "name": "Digital Storage (SI & IEC)",
        "description": "Binary data capacity and file sizing",
        "units": [
            {"id": "bit", "label": "Bit", "symbol": "b", "expr": "bit"},
            {"id": "byte", "label": "Byte", "symbol": "B", "expr": "byte"},
            {"id": "kbit", "label": "Kilobit (SI)", "symbol": "kbit", "expr": "kilobit"},
            {"id": "kB", "label": "Kilobyte (SI)", "symbol": "kB", "expr": "kilobyte"},
            {"id": "KiB", "label": "Kibibyte (IEC)", "symbol": "KiB", "expr": "kibibyte"},
            {"id": "Mbit", "label": "Megabit (SI)", "symbol": "Mbit", "expr": "megabit"},
            {"id": "MB", "label": "Megabyte (SI)", "symbol": "MB", "expr": "megabyte"},
            {"id": "MiB", "label": "Mebibyte (IEC)", "symbol": "MiB", "expr": "mebibyte"},
            {"id": "Gbit", "label": "Gigabit (SI)", "symbol": "Gbit", "expr": "gigabit"},
            {"id": "GB", "label": "Gigabyte (SI)", "symbol": "GB", "expr": "gigabyte"},
            {"id": "GiB", "label": "Gibibyte (IEC)", "symbol": "GiB", "expr": "gibibyte"},
            {"id": "Tbit", "label": "Terabit (SI)", "symbol": "Tbit", "expr": "terabit"},
            {"id": "TB", "label": "Terabyte (SI)", "symbol": "TB", "expr": "terabyte"},
            {"id": "TiB", "label": "Tebibyte (IEC)", "symbol": "TiB", "expr": "tebibyte"},
            {"id": "PB", "label": "Petabyte (SI)", "symbol": "PB", "expr": "petabyte"},
            {"id": "PiB", "label": "Pebibyte (IEC)", "symbol": "PiB", "expr": "pebibyte"},
        ],
    },
    {
        "id": "data_transfer",
        "name": "Data Transfer Rate",
        "description": "Network and bus bandwidth throughput",
        "units": [
            {"id": "bps", "label": "Bits per Second", "symbol": "bps", "expr": "bit / second"},
            {"id": "kbps", "label": "Kilobits per Second", "symbol": "kbps", "expr": "kilobit / second"},
            {"id": "Mbps", "label": "Megabits per Second", "symbol": "Mbps", "expr": "megabit / second"},
            {"id": "Gbps", "label": "Gigabits per Second", "symbol": "Gbps", "expr": "gigabit / second"},
            {"id": "B_s", "label": "Bytes per Second", "symbol": "B/s", "expr": "byte / second"},
            {"id": "kB_s", "label": "Kilobytes per Second", "symbol": "kB/s", "expr": "kilobyte / second"},
            {"id": "KiB_s", "label": "Kibibytes per Second", "symbol": "KiB/s", "expr": "kibibyte / second"},
            {"id": "MB_s", "label": "Megabytes per Second", "symbol": "MB/s", "expr": "megabyte / second"},
            {"id": "MiB_s", "label": "Mebibytes per Second", "symbol": "MiB/s", "expr": "mebibyte / second"},
            {"id": "GB_s", "label": "Gigabytes per Second", "symbol": "GB/s", "expr": "gigabyte / second"},
        ],
    },
    {
        "id": "electromagnetism_vcr",
        "name": "Voltage, Current & Resistance",
        "description": "Ohmic electrical circuits",
        "units": [
            {"id": "V", "label": "Volt", "symbol": "V", "expr": "volt"},
            {"id": "mV", "label": "Millivolt", "symbol": "mV", "expr": "millivolt"},
            {"id": "kV", "label": "Kilovolt", "symbol": "kV", "expr": "kilovolt"},
            {"id": "A", "label": "Ampere", "symbol": "A", "expr": "ampere"},
            {"id": "mA", "label": "Milliampere", "symbol": "mA", "expr": "milliampere"},
            {"id": "uA", "label": "Microampere", "symbol": "uA", "expr": "microampere"},
            {"id": "kA", "label": "Kiloampere", "symbol": "kA", "expr": "kiloampere"},
            {"id": "ohm", "label": "Ohm", "symbol": "\u03a9", "expr": "ohm"},
            {"id": "kohm", "label": "Kiloohm", "symbol": "k\u03a9", "expr": "kiloohm"},
            {"id": "Mohm", "label": "Megaohm", "symbol": "M\u03a9", "expr": "megaohm"},
            {"id": "S", "label": "Siemens", "symbol": "S", "expr": "siemens"},
        ],
    },
    {
        "id": "capacitance_charge",
        "name": "Capacitance, Inductance & Charge",
        "description": "Reactive circuit components and charge",
        "units": [
            {"id": "F", "label": "Farad", "symbol": "F", "expr": "farad"},
            {"id": "uF", "label": "Microfarad", "symbol": "uF", "expr": "microfarad"},
            {"id": "nF", "label": "Nanofarad", "symbol": "nF", "expr": "nanofarad"},
            {"id": "pF", "label": "Picofarad", "symbol": "pF", "expr": "picofarad"},
            {"id": "H", "label": "Henry", "symbol": "H", "expr": "henry"},
            {"id": "mH", "label": "Millihenry", "symbol": "mH", "expr": "millihenry"},
            {"id": "uH", "label": "Microhenry", "symbol": "uH", "expr": "microhenry"},
            {"id": "C", "label": "Coulomb", "symbol": "C", "expr": "coulomb"},
            {"id": "Ah", "label": "Ampere-Hour", "symbol": "Ah", "expr": "ampere * hour"},
            {"id": "mAh", "label": "Milliampere-Hour", "symbol": "mAh", "expr": "milliampere * hour"},
        ],
    },
    {
        "id": "radiation_optics",
        "name": "Magnetic, Optical & Radiation",
        "description": "Magnetic flux, photometry, and radiation dosage",
        "units": [
            {"id": "T", "label": "Tesla", "symbol": "T", "expr": "tesla"},
            {"id": "gauss", "label": "Gauss", "symbol": "G", "expr": "gauss"},
            {"id": "Wb", "label": "Weber", "symbol": "Wb", "expr": "weber"},
            {"id": "lx", "label": "Lux", "symbol": "lx", "expr": "lux"},
            {"id": "lm", "label": "Lumen", "symbol": "lm", "expr": "lumen"},
            {"id": "cd", "label": "Candela", "symbol": "cd", "expr": "candela"},
            {"id": "Bq", "label": "Becquerel", "symbol": "Bq", "expr": "becquerel"},
            {"id": "Ci", "label": "Curie", "symbol": "Ci", "expr": "curie"},
            {"id": "Gy", "label": "Gray", "symbol": "Gy", "expr": "gray"},
            {"id": "Sv", "label": "Sievert", "symbol": "Sv", "expr": "sievert"},
        ],
    },
]

ALIAS_MAP: dict[str, str] = {
    "c": "degC",
    "celsius": "degC",
    "\u00b0c": "degC",
    "f": "degF",
    "fahrenheit": "degF",
    "\u00b0f": "degF",
    "k": "kelvin",
    "b": "bit",
    "B": "byte",
    "kb": "kilobyte",
    "KB": "kilobyte",
    "mb": "megabyte",
    "MB": "megabyte",
    "gb": "gigabyte",
    "GB": "gigabyte",
    "tb": "terabyte",
    "TB": "terabyte",
    "kib": "kibibyte",
    "KiB": "kibibyte",
    "mib": "mebibyte",
    "MiB": "mebibyte",
    "gib": "gibibyte",
    "GiB": "gibibyte",
    "tib": "tebibyte",
    "TiB": "tebibyte",
}


def sanitize_error_message(exc: Exception) -> str:
    """Return a user-facing message for a conversion failure without backend package names."""
    text = str(exc).strip() or "Conversion failed."
    text = re.sub(r"\bpint(\.\w+)+", "unit error", text)
    return text


def normalize_unit_identifier(unit_code: str) -> str:
    # Resolve unit aliases and common abbreviations into canonical unit identifiers.
    cleaned = unit_code.strip()
    if cleaned in ALIAS_MAP:
        return ALIAS_MAP[cleaned]
    if cleaned.lower() in ALIAS_MAP:
        return ALIAS_MAP[cleaned.lower()]
    for category in CATEGORIES:
        for unit_item in category["units"]:
            if unit_item["id"].lower() == cleaned.lower():
                return str(unit_item["expr"])
            if unit_item["symbol"].lower() == cleaned.lower():
                return str(unit_item["expr"])
    return cleaned


def format_magnitude(val: float, mode: str = "standard", sig_figs: int = 7) -> str:
    # Format numerical magnitude according to selected precision mode.
    if val == 0:
        return "0"
    abs_val = abs(val)
    if mode == "scientific":
        return f"{val:.{max(1, sig_figs - 1)}e}"
    if mode == "fixed":
        return f"{val:.{max(0, sig_figs)}f}"
    if mode == "engineering":
        exp = int(math.floor(math.log10(abs_val)))
        eng_exp = (exp // 3) * 3
        mantissa = val / (10 ** eng_exp)
        return f"{mantissa:.{max(1, sig_figs - 1)}f}e{eng_exp:+d}"
    if 0.0001 <= abs_val < 1000000:
        formatted = f"{val:.{sig_figs}g}"
        if "e" not in formatted and "." in formatted:
            formatted = formatted.rstrip("0").rstrip(".")
        return formatted
    return f"{val:.{max(1, sig_figs - 1)}e}"


_UNIT_CATALOG_CACHE: dict[str, Any] | None = None


def get_unit_catalog() -> dict[str, Any]:
    # Return structured categories and full searchable list of units with caching.
    global _UNIT_CATALOG_CACHE
    if _UNIT_CATALOG_CACHE is not None:
        return _UNIT_CATALOG_CACHE

    ureg = get_ureg()
    categories_output: list[dict[str, Any]] = []
    for cat in CATEGORIES:
        enriched_units: list[dict[str, Any]] = []
        for u_item in cat["units"]:
            expr_str = str(u_item["expr"])
            dim_str = ""
            try:
                dim_str = str(ureg(expr_str).dimensionality)
            except Exception:
                dim_str = "[]"
            enriched_units.append({
                "id": u_item["id"],
                "label": u_item["label"],
                "symbol": u_item["symbol"],
                "expr": expr_str,
                "dimensionality": dim_str,
            })
        categories_output.append({
            "id": cat["id"],
            "name": cat["name"],
            "description": cat["description"],
            "unit_count": len(enriched_units),
            "units": enriched_units,
        })

    prefixes: list[dict[str, str]] = [
        {"name": "yocto", "symbol": "y", "factor": "1e-24"},
        {"name": "zepto", "symbol": "z", "factor": "1e-21"},
        {"name": "atto", "symbol": "a", "factor": "1e-18"},
        {"name": "femto", "symbol": "f", "factor": "1e-15"},
        {"name": "pico", "symbol": "p", "factor": "1e-12"},
        {"name": "nano", "symbol": "n", "factor": "1e-9"},
        {"name": "micro", "symbol": "u", "factor": "1e-6"},
        {"name": "milli", "symbol": "m", "factor": "1e-3"},
        {"name": "centi", "symbol": "c", "factor": "1e-2"},
        {"name": "deci", "symbol": "d", "factor": "1e-1"},
        {"name": "kilo", "symbol": "k", "factor": "1e3"},
        {"name": "mega", "symbol": "M", "factor": "1e6"},
        {"name": "giga", "symbol": "G", "factor": "1e9"},
        {"name": "tera", "symbol": "T", "factor": "1e12"},
        {"name": "peta", "symbol": "P", "factor": "1e15"},
        {"name": "exa", "symbol": "E", "factor": "1e18"},
        {"name": "kibi", "symbol": "Ki", "factor": "1024"},
        {"name": "mebi", "symbol": "Mi", "factor": "1024^2"},
        {"name": "gibi", "symbol": "Gi", "factor": "1024^3"},
        {"name": "tebi", "symbol": "Ti", "factor": "1024^4"},
    ]

    _UNIT_CATALOG_CACHE = {
        "categories": categories_output,
        "prefixes": prefixes,
    }
    return _UNIT_CATALOG_CACHE


def convert_unit_value(
    value: float,
    from_unit: str,
    to_unit: str,
    fmt_mode: str = "standard",
    sig_figs: int = 7,
) -> dict[str, Any]:
    # Convert numerical value between compatible units with dimensional safety.
    norm_from = normalize_unit_identifier(from_unit)
    norm_to = normalize_unit_identifier(to_unit)

    is_from_inv = norm_from in ("L/100km", "L / 100 km", "L / (100 km)")
    is_to_inv = norm_to in ("L/100km", "L / 100 km", "L / (100 km)")
    is_from_mpg = norm_from in ("mpg", "mile / gallon")
    is_to_mpg = norm_to in ("mpg", "mile / gallon")

    if is_from_inv and is_to_mpg:
        res = 235.214583 / value if value != 0 else 0.0
        return {
            "result": res,
            "formatted": format_magnitude(res, fmt_mode, sig_figs),
            "formula_str": f"{value} L/100km = {res:.4f} mpg",
            "dimensionality": "[length] / [volume]",
            "si_base": "m / m\u00b3",
        }
    if is_from_mpg and is_to_inv:
        res = 235.214583 / value if value != 0 else 0.0
        return {
            "result": res,
            "formatted": format_magnitude(res, fmt_mode, sig_figs),
            "formula_str": f"{value} mpg = {res:.4f} L/100km",
            "dimensionality": "[volume] / [length]",
            "si_base": "m\u00b3 / m",
        }

    quantity = get_ureg().Quantity(value, norm_from)
    converted = quantity.to(norm_to)
    result_val = float(converted.magnitude)

    dim_str = str(quantity.dimensionality)
    si_base_str = str(converted.to_base_units().units)
    formatted_str = format_magnitude(result_val, fmt_mode, sig_figs)
    formula_str = f"{value} {from_unit} = {formatted_str} {to_unit}"

    return {
        "result": result_val,
        "formatted": formatted_str,
        "formula_str": formula_str,
        "dimensionality": dim_str,
        "si_base": si_base_str,
    }


def convert_to_compatible_units(
    value: float,
    from_unit: str,
    category_id: str = "",
    include_all: bool = False,
    fmt_mode: str = "standard",
    sig_figs: int = 7,
) -> list[dict[str, Any]]:
    # Convert input value simultaneously into all compatible dimension units.
    norm_from = normalize_unit_identifier(from_unit)
    target_units: list[tuple[str, str, str]] = []

    if category_id:
        for cat in CATEGORIES:
            if cat["id"] == category_id:
                for u_item in cat["units"]:
                    target_units.append((u_item["id"], u_item["label"], u_item["symbol"]))
                break

    if not target_units or include_all:
        with contextlib.suppress(Exception):
            compat = get_ureg().get_compatible_units(norm_from)
            for unit_obj in compat:
                unit_name = str(unit_obj)
                if not any(t[0] == unit_name for t in target_units):
                    target_units.append((unit_name, unit_name.replace("_", " ").title(), unit_name))

    results: list[dict[str, Any]] = []
    for u_id, label, sym in target_units:
        try:
            res_dict = convert_unit_value(value, norm_from, u_id, fmt_mode=fmt_mode, sig_figs=sig_figs)
            results.append({
                "id": u_id,
                "label": label,
                "symbol": sym,
                "result": res_dict["result"],
                "formatted": res_dict["formatted"],
                "formula_str": res_dict["formula_str"],
                "dimensionality": res_dict["dimensionality"],
            })
        except Exception:
            continue

    return results


def convert_expression(
    expression: str,
    target_unit: str = "",
    fmt_mode: str = "standard",
    sig_figs: int = 7,
) -> dict[str, Any]:
    # Evaluate compound physical quantities and dimensional equations.
    parsed = get_expr_ureg()(expression)
    if target_unit and target_unit.strip():
        norm_target = normalize_unit_identifier(target_unit.strip())
        converted = parsed.to(norm_target)
    else:
        converted = parsed.to_base_units()

    res_val = float(converted.magnitude)
    unit_str = str(converted.units)
    dim_str = str(converted.dimensionality)
    formatted_val = format_magnitude(res_val, fmt_mode, sig_figs)

    return {
        "result": res_val,
        "unit": unit_str,
        "formatted": f"{formatted_val} {unit_str}",
        "dimensionality": dim_str,
        "si_base": str(converted.to_base_units().units),
    }

