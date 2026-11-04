"""Unit converter operations powered by Pint for dimensional analysis and precision arithmetic."""
from __future__ import annotations

import math
from typing import Any

import pint

UREG: pint.UnitRegistry = pint.UnitRegistry(autoconvert_offset_to_baseunit=False)
EXPR_UREG: pint.UnitRegistry = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)

try:
    UREG.define("mpg = mile / gallon = MPG")
    EXPR_UREG.define("mpg = mile / gallon = MPG")
except (ValueError, pint.errors.RedefinitionError):
    pass

CATEGORIES: list[dict[str, Any]] = [
    {
        "id": "length",
        "name": "Length",
        "description": "Distances and linear dimensions",
        "units": [
            {"id": "m", "label": "Meter", "symbol": "m", "pint": "meter"},
            {"id": "km", "label": "Kilometer", "symbol": "km", "pint": "kilometer"},
            {"id": "cm", "label": "Centimeter", "symbol": "cm", "pint": "centimeter"},
            {"id": "mm", "label": "Millimeter", "symbol": "mm", "pint": "millimeter"},
            {"id": "um", "label": "Micrometer", "symbol": "um", "pint": "micrometer"},
            {"id": "nm", "label": "Nanometer", "symbol": "nm", "pint": "nanometer"},
            {"id": "angstrom", "label": "Angstrom", "symbol": "\u00c5", "pint": "angstrom"},
            {"id": "in", "label": "Inch", "symbol": "in", "pint": "inch"},
            {"id": "ft", "label": "Foot", "symbol": "ft", "pint": "foot"},
            {"id": "yd", "label": "Yard", "symbol": "yd", "pint": "yard"},
            {"id": "mi", "label": "Mile", "symbol": "mi", "pint": "mile"},
            {"id": "nautical_mile", "label": "Nautical Mile", "symbol": "nmi", "pint": "nautical_mile"},
            {"id": "light_year", "label": "Light Year", "symbol": "ly", "pint": "light_year"},
            {"id": "parsec", "label": "Parsec", "symbol": "pc", "pint": "parsec"},
        ],
    },
    {
        "id": "area",
        "name": "Area",
        "description": "Surface areas and real estate plots",
        "units": [
            {"id": "m2", "label": "Square Meter", "symbol": "m\u00b2", "pint": "meter ** 2"},
            {"id": "km2", "label": "Square Kilometer", "symbol": "km\u00b2", "pint": "kilometer ** 2"},
            {"id": "cm2", "label": "Square Centimeter", "symbol": "cm\u00b2", "pint": "centimeter ** 2"},
            {"id": "mm2", "label": "Square Millimeter", "symbol": "mm\u00b2", "pint": "millimeter ** 2"},
            {"id": "ha", "label": "Hectare", "symbol": "ha", "pint": "hectare"},
            {"id": "acre", "label": "Acre", "symbol": "acre", "pint": "acre"},
            {"id": "in2", "label": "Square Inch", "symbol": "in\u00b2", "pint": "inch ** 2"},
            {"id": "ft2", "label": "Square Foot", "symbol": "ft\u00b2", "pint": "foot ** 2"},
            {"id": "yd2", "label": "Square Yard", "symbol": "yd\u00b2", "pint": "yard ** 2"},
            {"id": "mi2", "label": "Square Mile", "symbol": "mi\u00b2", "pint": "mile ** 2"},
        ],
    },
    {
        "id": "volume",
        "name": "Volume & Capacity",
        "description": "Fluid, gas, and solid space dimensions",
        "units": [
            {"id": "L", "label": "Liter", "symbol": "L", "pint": "liter"},
            {"id": "mL", "label": "Milliliter", "symbol": "mL", "pint": "milliliter"},
            {"id": "m3", "label": "Cubic Meter", "symbol": "m\u00b3", "pint": "meter ** 3"},
            {"id": "cm3", "label": "Cubic Centimeter", "symbol": "cm\u00b3", "pint": "centimeter ** 3"},
            {"id": "uL", "label": "Microliter", "symbol": "uL", "pint": "microliter"},
            {"id": "gal", "label": "Gallon (US)", "symbol": "gal", "pint": "gallon"},
            {"id": "qt", "label": "Quart (US)", "symbol": "qt", "pint": "quart"},
            {"id": "pt", "label": "Pint (US)", "symbol": "pt", "pint": "pint"},
            {"id": "cup", "label": "Cup (US)", "symbol": "cup", "pint": "cup"},
            {"id": "fl_oz", "label": "Fluid Ounce (US)", "symbol": "fl oz", "pint": "fluid_ounce"},
            {"id": "tbsp", "label": "Tablespoon (US)", "symbol": "tbsp", "pint": "tablespoon"},
            {"id": "tsp", "label": "Teaspoon (US)", "symbol": "tsp", "pint": "teaspoon"},
            {"id": "ft3", "label": "Cubic Foot", "symbol": "ft\u00b3", "pint": "foot ** 3"},
            {"id": "in3", "label": "Cubic Inch", "symbol": "in\u00b3", "pint": "inch ** 3"},
            {"id": "bbl", "label": "Oil Barrel (US)", "symbol": "bbl", "pint": "barrel"},
        ],
    },
    {
        "id": "mass",
        "name": "Mass & Weight",
        "description": "Quantities of matter and gravitational weights",
        "units": [
            {"id": "kg", "label": "Kilogram", "symbol": "kg", "pint": "kilogram"},
            {"id": "g", "label": "Gram", "symbol": "g", "pint": "gram"},
            {"id": "mg", "label": "Milligram", "symbol": "mg", "pint": "milligram"},
            {"id": "ug", "label": "Microgram", "symbol": "ug", "pint": "microgram"},
            {"id": "t", "label": "Metric Ton", "symbol": "t", "pint": "metric_ton"},
            {"id": "lb", "label": "Pound", "symbol": "lb", "pint": "pound"},
            {"id": "oz", "label": "Ounce", "symbol": "oz", "pint": "ounce"},
            {"id": "grain", "label": "Grain", "symbol": "gr", "pint": "grain"},
            {"id": "carat", "label": "Carat", "symbol": "ct", "pint": "carat"},
            {"id": "slug", "label": "Slug", "symbol": "slug", "pint": "slug"},
            {"id": "short_ton", "label": "Short Ton (US)", "symbol": "ton", "pint": "short_ton"},
            {"id": "long_ton", "label": "Long Ton (UK)", "symbol": "long ton", "pint": "long_ton"},
        ],
    },
    {
        "id": "time",
        "name": "Time",
        "description": "Temporal durations and intervals",
        "units": [
            {"id": "s", "label": "Second", "symbol": "s", "pint": "second"},
            {"id": "ms", "label": "Millisecond", "symbol": "ms", "pint": "millisecond"},
            {"id": "us", "label": "Microsecond", "symbol": "us", "pint": "microsecond"},
            {"id": "ns", "label": "Nanosecond", "symbol": "ns", "pint": "nanosecond"},
            {"id": "min", "label": "Minute", "symbol": "min", "pint": "minute"},
            {"id": "hr", "label": "Hour", "symbol": "hr", "pint": "hour"},
            {"id": "day", "label": "Day", "symbol": "d", "pint": "day"},
            {"id": "week", "label": "Week", "symbol": "wk", "pint": "week"},
            {"id": "month", "label": "Month (30 days)", "symbol": "mo", "pint": "month"},
            {"id": "year", "label": "Year (Julian)", "symbol": "yr", "pint": "year"},
        ],
    },
    {
        "id": "temperature",
        "name": "Temperature",
        "description": "Thermal scales and thermodynamic states",
        "units": [
            {"id": "degC", "label": "Celsius", "symbol": "\u00b0C", "pint": "degC"},
            {"id": "degF", "label": "Fahrenheit", "symbol": "\u00b0F", "pint": "degF"},
            {"id": "kelvin", "label": "Kelvin", "symbol": "K", "pint": "kelvin"},
            {"id": "degR", "label": "Rankine", "symbol": "\u00b0R", "pint": "degR"},
        ],
    },
    {
        "id": "speed",
        "name": "Speed & Velocity",
        "description": "Linear rates of motion",
        "units": [
            {"id": "m_s", "label": "Meters per Second", "symbol": "m/s", "pint": "meter / second"},
            {"id": "km_h", "label": "Kilometers per Hour", "symbol": "km/h", "pint": "kilometer / hour"},
            {"id": "mph", "label": "Miles per Hour", "symbol": "mph", "pint": "mile / hour"},
            {"id": "knot", "label": "Knot", "symbol": "kn", "pint": "knot"},
            {"id": "ft_s", "label": "Feet per Second", "symbol": "ft/s", "pint": "foot / second"},
            {"id": "c", "label": "Speed of Light", "symbol": "c", "pint": "speed_of_light"},
        ],
    },
    {
        "id": "acceleration",
        "name": "Acceleration",
        "description": "Rates of velocity change",
        "units": [
            {"id": "m_s2", "label": "Meters per Second Squared", "symbol": "m/s\u00b2", "pint": "meter / second ** 2"},
            {"id": "ft_s2", "label": "Feet per Second Squared", "symbol": "ft/s\u00b2", "pint": "foot / second ** 2"},
            {"id": "gravity", "label": "Standard Gravity", "symbol": "g", "pint": "standard_gravity"},
            {"id": "galileo", "label": "Galileo", "symbol": "Gal", "pint": "galileo"},
        ],
    },
    {
        "id": "force",
        "name": "Force",
        "description": "Mechanical forces and loads",
        "units": [
            {"id": "N", "label": "Newton", "symbol": "N", "pint": "newton"},
            {"id": "kN", "label": "Kilonewton", "symbol": "kN", "pint": "kilonewton"},
            {"id": "MN", "label": "Meganewton", "symbol": "MN", "pint": "meganewton"},
            {"id": "lbf", "label": "Pound-Force", "symbol": "lbf", "pint": "force_pound"},
            {"id": "kgf", "label": "Kilogram-Force", "symbol": "kgf", "pint": "force_kilogram"},
            {"id": "dyn", "label": "Dyne", "symbol": "dyn", "pint": "dyne"},
            {"id": "poundal", "label": "Poundal", "symbol": "pdl", "pint": "poundal"},
        ],
    },
    {
        "id": "pressure",
        "name": "Pressure & Mechanical Stress",
        "description": "Force per unit area and stress",
        "units": [
            {"id": "Pa", "label": "Pascal", "symbol": "Pa", "pint": "pascal"},
            {"id": "kPa", "label": "Kilopascal", "symbol": "kPa", "pint": "kilopascal"},
            {"id": "MPa", "label": "Megapascal", "symbol": "MPa", "pint": "megapascal"},
            {"id": "GPa", "label": "Gigapascal", "symbol": "GPa", "pint": "gigapascal"},
            {"id": "bar", "label": "Bar", "symbol": "bar", "pint": "bar"},
            {"id": "mbar", "label": "Millibar", "symbol": "mbar", "pint": "millibar"},
            {"id": "psi", "label": "Pounds per Square Inch", "symbol": "psi", "pint": "psi"},
            {"id": "ksi", "label": "Kilopounds per Square Inch", "symbol": "ksi", "pint": "ksi"},
            {"id": "atm", "label": "Standard Atmosphere", "symbol": "atm", "pint": "atmosphere"},
            {"id": "torr", "label": "Torr", "symbol": "Torr", "pint": "torr"},
            {"id": "mmHg", "label": "Millimeters of Mercury", "symbol": "mmHg", "pint": "millimeter_Hg"},
            {"id": "inHg", "label": "Inches of Mercury", "symbol": "inHg", "pint": "inch_Hg"},
        ],
    },
    {
        "id": "energy",
        "name": "Energy, Work & Heat",
        "description": "Thermal, kinetic, electrical, and chemical energy",
        "units": [
            {"id": "J", "label": "Joule", "symbol": "J", "pint": "joule"},
            {"id": "kJ", "label": "Kilojoule", "symbol": "kJ", "pint": "kilojoule"},
            {"id": "MJ", "label": "Megajoule", "symbol": "MJ", "pint": "megajoule"},
            {"id": "Wh", "label": "Watt-Hour", "symbol": "Wh", "pint": "watt_hour"},
            {"id": "kWh", "label": "Kilowatt-Hour", "symbol": "kWh", "pint": "kilowatt_hour"},
            {"id": "MWh", "label": "Megawatt-Hour", "symbol": "MWh", "pint": "megawatt_hour"},
            {"id": "cal", "label": "Calorie (Thermochemical)", "symbol": "cal", "pint": "calorie"},
            {"id": "kcal", "label": "Kilocalorie / Food Calorie", "symbol": "kcal", "pint": "kilocalorie"},
            {"id": "BTU", "label": "British Thermal Unit", "symbol": "BTU", "pint": "BTU"},
            {"id": "therm", "label": "Therm (US)", "symbol": "therm", "pint": "therm"},
            {"id": "eV", "label": "Electronvolt", "symbol": "eV", "pint": "electron_volt"},
            {"id": "keV", "label": "Kiloelectronvolt", "symbol": "keV", "pint": "kiloelectron_volt"},
            {"id": "MeV", "label": "Megaelectronvolt", "symbol": "MeV", "pint": "megaelectron_volt"},
            {"id": "ft_lbf", "label": "Foot-Pound", "symbol": "ft\u22c5lbf", "pint": "foot * force_pound"},
            {"id": "erg", "label": "Erg", "symbol": "erg", "pint": "erg"},
        ],
    },
    {
        "id": "power",
        "name": "Power",
        "description": "Rate of doing work or transferring energy",
        "units": [
            {"id": "W", "label": "Watt", "symbol": "W", "pint": "watt"},
            {"id": "kW", "label": "Kilowatt", "symbol": "kW", "pint": "kilowatt"},
            {"id": "MW", "label": "Megawatt", "symbol": "MW", "pint": "megawatt"},
            {"id": "GW", "label": "Gigawatt", "symbol": "GW", "pint": "gigawatt"},
            {"id": "hp", "label": "Mechanical Horsepower", "symbol": "hp", "pint": "horsepower"},
            {"id": "metric_hp", "label": "Metric Horsepower", "symbol": "PS", "pint": "metric_horsepower"},
            {"id": "BTU_hr", "label": "BTU per Hour", "symbol": "BTU/h", "pint": "BTU / hour"},
            {"id": "ton_ref", "label": "Ton of Refrigeration", "symbol": "TR", "pint": "refrigeration_ton"},
        ],
    },
    {
        "id": "torque",
        "name": "Torque & Moment",
        "description": "Rotational forces and couples",
        "units": [
            {"id": "N_m", "label": "Newton-Meter", "symbol": "N\u22c5m", "pint": "newton * meter"},
            {"id": "kN_m", "label": "Kilonewton-Meter", "symbol": "kN\u22c5m", "pint": "kilonewton * meter"},
            {"id": "lbf_ft", "label": "Foot-Pound", "symbol": "lbf\u22c5ft", "pint": "force_pound * foot"},
            {"id": "lbf_in", "label": "Inch-Pound", "symbol": "lbf\u22c5in", "pint": "force_pound * inch"},
            {"id": "kgf_m", "label": "Kilogram-Force Meter", "symbol": "kgf\u22c5m", "pint": "force_kilogram * meter"},
        ],
    },
    {
        "id": "angle",
        "name": "Plane & Solid Angle",
        "description": "Geometric rotation and spherical sectors",
        "units": [
            {"id": "deg", "label": "Degree", "symbol": "\u00b0", "pint": "degree"},
            {"id": "rad", "label": "Radian", "symbol": "rad", "pint": "radian"},
            {"id": "grad", "label": "Gradian", "symbol": "grad", "pint": "gradian"},
            {"id": "arcmin", "label": "Arcminute", "symbol": "'", "pint": "arcminute"},
            {"id": "arcsec", "label": "Arcsecond", "symbol": "\"", "pint": "arcsecond"},
            {"id": "turn", "label": "Turn / Revolution", "symbol": "tr", "pint": "turn"},
            {"id": "sr", "label": "Steradian", "symbol": "sr", "pint": "steradian"},
        ],
    },
    {
        "id": "frequency",
        "name": "Frequency & Angular Speed",
        "description": "Cyclic repetition rates",
        "units": [
            {"id": "Hz", "label": "Hertz", "symbol": "Hz", "pint": "hertz"},
            {"id": "kHz", "label": "Kilohertz", "symbol": "kHz", "pint": "kilohertz"},
            {"id": "MHz", "label": "Megahertz", "symbol": "MHz", "pint": "megahertz"},
            {"id": "GHz", "label": "Gigahertz", "symbol": "GHz", "pint": "gigahertz"},
            {"id": "THz", "label": "Terahertz", "symbol": "THz", "pint": "terahertz"},
            {"id": "rpm", "label": "Revolutions per Minute", "symbol": "RPM", "pint": "rpm"},
            {"id": "rad_s", "label": "Radians per Second", "symbol": "rad/s", "pint": "radian / second"},
        ],
    },
    {
        "id": "density",
        "name": "Density",
        "description": "Mass per unit volume",
        "units": [
            {"id": "kg_m3", "label": "Kilograms per Cubic Meter", "symbol": "kg/m\u00b3", "pint": "kilogram / meter ** 3"},
            {"id": "g_cm3", "label": "Grams per Cubic Centimeter", "symbol": "g/cm\u00b3", "pint": "gram / centimeter ** 3"},
            {"id": "g_mL", "label": "Grams per Milliliter", "symbol": "g/mL", "pint": "gram / milliliter"},
            {"id": "lb_ft3", "label": "Pounds per Cubic Foot", "symbol": "lb/ft\u00b3", "pint": "pound / foot ** 3"},
            {"id": "lb_in3", "label": "Pounds per Cubic Inch", "symbol": "lb/in\u00b3", "pint": "pound / inch ** 3"},
            {"id": "lb_gal", "label": "Pounds per Gallon (US)", "symbol": "lb/gal", "pint": "pound / gallon"},
        ],
    },
    {
        "id": "mass_flow",
        "name": "Mass Flow Rate",
        "description": "Rate of mass transit per unit time",
        "units": [
            {"id": "kg_s", "label": "Kilograms per Second", "symbol": "kg/s", "pint": "kilogram / second"},
            {"id": "kg_h", "label": "Kilograms per Hour", "symbol": "kg/h", "pint": "kilogram / hour"},
            {"id": "g_s", "label": "Grams per Second", "symbol": "g/s", "pint": "gram / second"},
            {"id": "lb_s", "label": "Pounds per Second", "symbol": "lb/s", "pint": "pound / second"},
            {"id": "lb_h", "label": "Pounds per Hour", "symbol": "lb/h", "pint": "pound / hour"},
            {"id": "t_h", "label": "Metric Tons per Hour", "symbol": "t/h", "pint": "metric_ton / hour"},
        ],
    },
    {
        "id": "volumetric_flow",
        "name": "Volumetric Flow Rate",
        "description": "Fluid and gas volume displacement rates",
        "units": [
            {"id": "m3_s", "label": "Cubic Meters per Second", "symbol": "m\u00b3/s", "pint": "meter ** 3 / second"},
            {"id": "m3_h", "label": "Cubic Meters per Hour", "symbol": "m\u00b3/h", "pint": "meter ** 3 / hour"},
            {"id": "L_s", "label": "Liters per Second", "symbol": "L/s", "pint": "liter / second"},
            {"id": "L_min", "label": "Liters per Minute", "symbol": "L/min", "pint": "liter / minute"},
            {"id": "gpm", "label": "Gallons per Minute (US)", "symbol": "GPM", "pint": "gallon / minute"},
            {"id": "cfm", "label": "Cubic Feet per Minute", "symbol": "CFM", "pint": "foot ** 3 / minute"},
            {"id": "bbl_day", "label": "Barrels per Day", "symbol": "bpd", "pint": "barrel / day"},
        ],
    },
    {
        "id": "dynamic_viscosity",
        "name": "Dynamic Viscosity",
        "description": "Fluid internal resistance to shear flow",
        "units": [
            {"id": "Pa_s", "label": "Pascal-Second", "symbol": "Pa\u22c5s", "pint": "pascal * second"},
            {"id": "mPa_s", "label": "Millipascal-Second", "symbol": "mPa\u22c5s", "pint": "millipascal * second"},
            {"id": "P", "label": "Poise", "symbol": "P", "pint": "poise"},
            {"id": "cP", "label": "Centipoise", "symbol": "cP", "pint": "centipoise"},
            {"id": "lbf_s_ft2", "label": "Pound-Force Second per Sq Foot", "symbol": "lbf\u22c5s/ft\u00b2", "pint": "force_pound * second / foot ** 2"},
        ],
    },
    {
        "id": "kinematic_viscosity",
        "name": "Kinematic Viscosity",
        "description": "Fluid momentum diffusivity",
        "units": [
            {"id": "m2_s", "label": "Square Meters per Second", "symbol": "m\u00b2/s", "pint": "meter ** 2 / second"},
            {"id": "mm2_s", "label": "Square Millimeters per Second", "symbol": "mm\u00b2/s", "pint": "millimeter ** 2 / second"},
            {"id": "St", "label": "Stokes", "symbol": "St", "pint": "stokes"},
            {"id": "cSt", "label": "Centistokes", "symbol": "cSt", "pint": "centistokes"},
            {"id": "ft2_s", "label": "Square Feet per Second", "symbol": "ft\u00b2/s", "pint": "foot ** 2 / second"},
        ],
    },
    {
        "id": "surface_tension",
        "name": "Surface Tension",
        "description": "Interfacial tension per unit length",
        "units": [
            {"id": "N_m", "label": "Newtons per Meter", "symbol": "N/m", "pint": "newton / meter"},
            {"id": "mN_m", "label": "Millinewtons per Meter", "symbol": "mN/m", "pint": "millinewton / meter"},
            {"id": "dyn_cm", "label": "Dynes per Centimeter", "symbol": "dyn/cm", "pint": "dyne / centimeter"},
            {"id": "lbf_in", "label": "Pound-Force per Inch", "symbol": "lbf/in", "pint": "force_pound / inch"},
        ],
    },
    {
        "id": "thermal_conductivity",
        "name": "Thermal Conductivity",
        "description": "Material thermal conduction coefficient",
        "units": [
            {"id": "W_m_K", "label": "Watts per Meter-Kelvin", "symbol": "W/(m\u22c5K)", "pint": "watt / (meter * kelvin)"},
            {"id": "BTU_hr_ft_F", "label": "BTU per Hour-Foot-DegF", "symbol": "BTU/(h\u22c5ft\u22c5\u00b0F)", "pint": "BTU / (hour * foot * delta_degF)"},
            {"id": "cal_s_cm_C", "label": "Calories per Sec-Centimeter-DegC", "symbol": "cal/(s\u22c5cm\u22c5\u00b0C)", "pint": "calorie / (second * centimeter * delta_degC)"},
        ],
    },
    {
        "id": "heat_transfer",
        "name": "Heat Transfer Coefficient",
        "description": "Convective thermal conductance per unit area",
        "units": [
            {"id": "W_m2_K", "label": "Watts per Sq Meter-Kelvin", "symbol": "W/(m\u00b2\u22c5K)", "pint": "watt / (meter ** 2 * kelvin)"},
            {"id": "BTU_hr_ft2_F", "label": "BTU per Hour-Sq Foot-DegF", "symbol": "BTU/(h\u22c5ft\u00b2\u22c5\u00b0F)", "pint": "BTU / (hour * foot ** 2 * delta_degF)"},
        ],
    },
    {
        "id": "specific_heat",
        "name": "Specific Heat Capacity",
        "description": "Heat storage capacity per unit mass",
        "units": [
            {"id": "J_kg_K", "label": "Joules per Kilogram-Kelvin", "symbol": "J/(kg\u22c5K)", "pint": "joule / (kilogram * kelvin)"},
            {"id": "kJ_kg_K", "label": "Kilojoules per Kilogram-Kelvin", "symbol": "kJ/(kg\u22c5K)", "pint": "kilojoule / (kilogram * kelvin)"},
            {"id": "BTU_lb_F", "label": "BTU per Pound-DegF", "symbol": "BTU/(lb\u22c5\u00b0F)", "pint": "BTU / (pound * delta_degF)"},
            {"id": "cal_g_C", "label": "Calories per Gram-DegC", "symbol": "cal/(g\u22c5\u00b0C)", "pint": "calorie / (gram * delta_degC)"},
        ],
    },
    {
        "id": "fuel_economy",
        "name": "Fuel Economy",
        "description": "Vehicle fuel efficiency and consumption",
        "units": [
            {"id": "mpg", "label": "Miles per Gallon (US)", "symbol": "mpg", "pint": "mpg"},
            {"id": "km_L", "label": "Kilometers per Liter", "symbol": "km/L", "pint": "kilometer / liter"},
            {"id": "L_100km", "label": "Liters per 100 km", "symbol": "L/100km", "pint": "L/100km"},
        ],
    },
    {
        "id": "digital_storage",
        "name": "Digital Storage (SI & IEC)",
        "description": "Binary data capacity and file sizing",
        "units": [
            {"id": "bit", "label": "Bit", "symbol": "b", "pint": "bit"},
            {"id": "byte", "label": "Byte", "symbol": "B", "pint": "byte"},
            {"id": "kbit", "label": "Kilobit (SI)", "symbol": "kbit", "pint": "kilobit"},
            {"id": "kB", "label": "Kilobyte (SI)", "symbol": "kB", "pint": "kilobyte"},
            {"id": "KiB", "label": "Kibibyte (IEC)", "symbol": "KiB", "pint": "kibibyte"},
            {"id": "Mbit", "label": "Megabit (SI)", "symbol": "Mbit", "pint": "megabit"},
            {"id": "MB", "label": "Megabyte (SI)", "symbol": "MB", "pint": "megabyte"},
            {"id": "MiB", "label": "Mebibyte (IEC)", "symbol": "MiB", "pint": "mebibyte"},
            {"id": "Gbit", "label": "Gigabit (SI)", "symbol": "Gbit", "pint": "gigabit"},
            {"id": "GB", "label": "Gigabyte (SI)", "symbol": "GB", "pint": "gigabyte"},
            {"id": "GiB", "label": "Gibibyte (IEC)", "symbol": "GiB", "pint": "gibibyte"},
            {"id": "Tbit", "label": "Terabit (SI)", "symbol": "Tbit", "pint": "terabit"},
            {"id": "TB", "label": "Terabyte (SI)", "symbol": "TB", "pint": "terabyte"},
            {"id": "TiB", "label": "Tebibyte (IEC)", "symbol": "TiB", "pint": "tebibyte"},
            {"id": "PB", "label": "Petabyte (SI)", "symbol": "PB", "pint": "petabyte"},
            {"id": "PiB", "label": "Pebibyte (IEC)", "symbol": "PiB", "pint": "pebibyte"},
        ],
    },
    {
        "id": "data_transfer",
        "name": "Data Transfer Rate",
        "description": "Network and bus bandwidth throughput",
        "units": [
            {"id": "bps", "label": "Bits per Second", "symbol": "bps", "pint": "bit / second"},
            {"id": "kbps", "label": "Kilobits per Second", "symbol": "kbps", "pint": "kilobit / second"},
            {"id": "Mbps", "label": "Megabits per Second", "symbol": "Mbps", "pint": "megabit / second"},
            {"id": "Gbps", "label": "Gigabits per Second", "symbol": "Gbps", "pint": "gigabit / second"},
            {"id": "B_s", "label": "Bytes per Second", "symbol": "B/s", "pint": "byte / second"},
            {"id": "kB_s", "label": "Kilobytes per Second", "symbol": "kB/s", "pint": "kilobyte / second"},
            {"id": "KiB_s", "label": "Kibibytes per Second", "symbol": "KiB/s", "pint": "kibibyte / second"},
            {"id": "MB_s", "label": "Megabytes per Second", "symbol": "MB/s", "pint": "megabyte / second"},
            {"id": "MiB_s", "label": "Mebibytes per Second", "symbol": "MiB/s", "pint": "mebibyte / second"},
            {"id": "GB_s", "label": "Gigabytes per Second", "symbol": "GB/s", "pint": "gigabyte / second"},
        ],
    },
    {
        "id": "electromagnetism_vcr",
        "name": "Voltage, Current & Resistance",
        "description": "Ohmic electrical circuits",
        "units": [
            {"id": "V", "label": "Volt", "symbol": "V", "pint": "volt"},
            {"id": "mV", "label": "Millivolt", "symbol": "mV", "pint": "millivolt"},
            {"id": "kV", "label": "Kilovolt", "symbol": "kV", "pint": "kilovolt"},
            {"id": "A", "label": "Ampere", "symbol": "A", "pint": "ampere"},
            {"id": "mA", "label": "Milliampere", "symbol": "mA", "pint": "milliampere"},
            {"id": "uA", "label": "Microampere", "symbol": "uA", "pint": "microampere"},
            {"id": "kA", "label": "Kiloampere", "symbol": "kA", "pint": "kiloampere"},
            {"id": "ohm", "label": "Ohm", "symbol": "\u03a9", "pint": "ohm"},
            {"id": "kohm", "label": "Kiloohm", "symbol": "k\u03a9", "pint": "kiloohm"},
            {"id": "Mohm", "label": "Megaohm", "symbol": "M\u03a9", "pint": "megaohm"},
            {"id": "S", "label": "Siemens", "symbol": "S", "pint": "siemens"},
        ],
    },
    {
        "id": "capacitance_charge",
        "name": "Capacitance, Inductance & Charge",
        "description": "Reactive circuit components and charge",
        "units": [
            {"id": "F", "label": "Farad", "symbol": "F", "pint": "farad"},
            {"id": "uF", "label": "Microfarad", "symbol": "uF", "pint": "microfarad"},
            {"id": "nF", "label": "Nanofarad", "symbol": "nF", "pint": "nanofarad"},
            {"id": "pF", "label": "Picofarad", "symbol": "pF", "pint": "picofarad"},
            {"id": "H", "label": "Henry", "symbol": "H", "pint": "henry"},
            {"id": "mH", "label": "Millihenry", "symbol": "mH", "pint": "millihenry"},
            {"id": "uH", "label": "Microhenry", "symbol": "uH", "pint": "microhenry"},
            {"id": "C", "label": "Coulomb", "symbol": "C", "pint": "coulomb"},
            {"id": "Ah", "label": "Ampere-Hour", "symbol": "Ah", "pint": "ampere * hour"},
            {"id": "mAh", "label": "Milliampere-Hour", "symbol": "mAh", "pint": "milliampere * hour"},
        ],
    },
    {
        "id": "radiation_optics",
        "name": "Magnetic, Optical & Radiation",
        "description": "Magnetic flux, photometry, and radiation dosage",
        "units": [
            {"id": "T", "label": "Tesla", "symbol": "T", "pint": "tesla"},
            {"id": "gauss", "label": "Gauss", "symbol": "G", "pint": "gauss"},
            {"id": "Wb", "label": "Weber", "symbol": "Wb", "pint": "weber"},
            {"id": "lx", "label": "Lux", "symbol": "lx", "pint": "lux"},
            {"id": "lm", "label": "Lumen", "symbol": "lm", "pint": "lumen"},
            {"id": "cd", "label": "Candela", "symbol": "cd", "pint": "candela"},
            {"id": "Bq", "label": "Becquerel", "symbol": "Bq", "pint": "becquerel"},
            {"id": "Ci", "label": "Curie", "symbol": "Ci", "pint": "curie"},
            {"id": "Gy", "label": "Gray", "symbol": "Gy", "pint": "gray"},
            {"id": "Sv", "label": "Sievert", "symbol": "Sv", "pint": "sievert"},
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


def normalize_unit_identifier(unit_code: str) -> str:
    # Resolve unit aliases and common abbreviations into canonical Pint identifiers.
    cleaned = unit_code.strip()
    if cleaned in ALIAS_MAP:
        return ALIAS_MAP[cleaned]
    if cleaned.lower() in ALIAS_MAP:
        return ALIAS_MAP[cleaned.lower()]
    for category in CATEGORIES:
        for unit_item in category["units"]:
            if unit_item["id"].lower() == cleaned.lower():
                return str(unit_item["pint"])
            if unit_item["symbol"].lower() == cleaned.lower():
                return str(unit_item["pint"])
    return cleaned


def format_magnitude(val: float, mode: str = "smart", sig_figs: int = 7) -> str:
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


def get_unit_catalog() -> dict[str, Any]:
    # Return structured categories and full searchable list of Pint units.
    categories_output: list[dict[str, Any]] = []
    for cat in CATEGORIES:
        enriched_units: list[dict[str, Any]] = []
        for u_item in cat["units"]:
            pint_str = str(u_item["pint"])
            dim_str = ""
            try:
                dim_str = str(UREG(pint_str).dimensionality)
            except Exception:
                dim_str = "[]"
            enriched_units.append({
                "id": u_item["id"],
                "label": u_item["label"],
                "symbol": u_item["symbol"],
                "pint": pint_str,
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

    return {
        "categories": categories_output,
        "prefixes": prefixes,
    }


def convert_unit_value(
    value: float,
    from_unit: str,
    to_unit: str,
    fmt_mode: str = "smart",
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

    quantity = UREG.Quantity(value, norm_from)
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
    include_all_pint: bool = False,
    fmt_mode: str = "smart",
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

    if not target_units or include_all_pint:
        try:
            compat = UREG.get_compatible_units(norm_from)
            for unit_obj in compat:
                unit_name = str(unit_obj)
                if not any(t[0] == unit_name for t in target_units):
                    target_units.append((unit_name, unit_name.replace("_", " ").title(), unit_name))
        except Exception:
            pass

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


def convert_pint_expression(
    expression: str,
    target_unit: str = "",
    fmt_mode: str = "smart",
    sig_figs: int = 7,
) -> dict[str, Any]:
    # Evaluate compound physical quantities and dimensional equations.
    parsed = EXPR_UREG(expression)
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

