"""Scheme and Sub-scheme configuration for Budget Management System

This module maintains backward compatibility while integrating with the new registry.
For new schemes, use the registry-based approach in src/schemes/.
"""
from typing import Dict, List, Tuple
from src.core.registry import scheme_registry

SCHEME_TYPES = {
    "charged": {"en": "Charged", "mr": "भारित"},
    "voted": {"en": "Voted", "mr": "दत्तमत"}
}

SCHEMES: Dict[str, Dict] = {
    "2029": {"name": "Land Revenue", "name_mr": "महसूल"},
    "2045": {"name": "Other Taxes and Duties on Commodities and Services", "name_mr": "वस्तू व सेवा इतर कर व शुल्क"},
    "2053": {"name": "District Administration", "name_mr": "जिल्हा प्रशासन"},
    "2075": {"name": "Miscellaneous General Services", "name_mr": "विविध सामान्य सेवा"},
    "2215": {"name": "Water Scarcity", "name_mr": "पाणी टंचाई"},
    "2235": {"name": "Social Security and Welfare", "name_mr": "सामाजिक सुरक्षा व कल्याण"},
    "2245": {"name": "Relief on account of Natural Calamities", "name_mr": "नैसर्गिक आपत्ती निवारण"},
    "6245": {"name": "Loans for Natural Calamities", "name_mr": "नैसर्गिक आपत्ती कर्ज"},
    "6401": {"name": "Loans for Crop Husbandry", "name_mr": "पीक उत्पादन कर्ज"},
    "7610": {"name": "Government Advances", "name_mr": "शासकीय अग्रिम"},
    "0029": {"name": "Land Revenue Receipts", "name_mr": "महसूल जमा"}
}

# Sub-schemes with type (charged/voted) and implementation status
# Format: {code: {scheme, type, implemented, name_mr}}
SUB_SCHEMES: Dict[str, Dict] = {
    # 2029 - Land Revenue
    "20290037": {"scheme": "2029", "type": "charged", "implemented": False, "name_mr": "२०२९००३७"},
    "20290046": {"scheme": "2029", "type": "voted", "implemented": False, "name_mr": "२०२९००४६"},
    "20290182": {"scheme": "2029", "type": "voted", "implemented": False, "name_mr": "२०२९०१८२"},
    "20290262": {"scheme": "2029", "type": "voted", "implemented": False, "name_mr": "२०२९०२६२"},
    
    # 2045 - Other Taxes
    "20450091": {"scheme": "2045", "type": "voted", "implemented": False, "name_mr": "२०४५००९१"},
    "20450182": {"scheme": "2045", "type": "voted", "implemented": False, "name_mr": "२०४५०१८२"},
    "20450251": {"scheme": "2045", "type": "voted", "implemented": False, "name_mr": "२०४५०२५१"},
    "20450262": {"scheme": "2045", "type": "voted", "implemented": False, "name_mr": "२०४५०२६२"},
    
    # 2053 - District Administration
    "20530019": {"scheme": "2053", "type": "charged", "implemented": True, "name_mr": "२०५३००१९"},
    "20530153": {"scheme": "2053", "type": "charged", "implemented": True, "name_mr": "२०५३०१५३"},
    "20530233": {"scheme": "2053", "type": "charged", "implemented": True, "name_mr": "२०५३०२३३"},
    "20530304": {"scheme": "2053", "type": "charged", "implemented": True, "name_mr": "२०५३०३०४"},
    "20530378": {"scheme": "2053", "type": "charged", "implemented": True, "name_mr": "२०५३०३७८"},
    "20530028": {"scheme": "2053", "type": "voted", "implemented": True, "name_mr": "२०५३००२८"},
    "20530162": {"scheme": "2053", "type": "voted", "implemented": True, "name_mr": "२०५३०१६२"},
    "20530242": {"scheme": "2053", "type": "voted", "implemented": False, "name_mr": "२०५३०२४२"},
    "20530313": {"scheme": "2053", "type": "voted", "implemented": False, "name_mr": "२०५३०३१३"},
    "20530387": {"scheme": "2053", "type": "voted", "implemented": False, "name_mr": "२०५३०३८७"},
    
    # 2075 - Miscellaneous General Services (Unified - no subschemes)
    # NOTE: 2075 is now unified like 2245. Entry point: /ui/s2075/expenditure
    
    # 2215 - Water Scarcity
    "2215": {"scheme": "2215", "type": "voted", "implemented": True, "name_mr": "२२१५"},
    
    # 2235 - Social Security and Welfare
    "22350338": {"scheme": "2235", "type": "voted", "implemented": False, "name_mr": "२२३५०३३८"},
    "22353195": {"scheme": "2235", "type": "voted", "implemented": False, "name_mr": "२२३५३१९५"},
    "22353408": {"scheme": "2235", "type": "voted", "implemented": False, "name_mr": "२२३५३४०८"},
    "22350311": {"scheme": "2235", "type": "voted", "implemented": False, "name_mr": "२२३५०३११"},
    
    # 6245 - Loans for Natural Calamities
    "62450017": {"scheme": "6245", "type": "voted", "implemented": True, "name_mr": "६२४५००१७"},
    
    # 6401 - Loans for Crop Husbandry
    "64010018": {"scheme": "6401", "type": "voted", "implemented": True, "name_mr": "६४०१००१८"},
    
    # 7610 - Government Advances
    "76100149": {"scheme": "7610", "type": "voted", "implemented": True, "name_mr": "७६१००१४९"},
    "76100158": {"scheme": "7610", "type": "voted", "implemented": True, "name_mr": "७६१००१५८"},
    "76100167": {"scheme": "7610", "type": "voted", "implemented": True, "name_mr": "७६१००१६७"},
    "76101871": {"scheme": "7610", "type": "voted", "implemented": True, "name_mr": "७६१०१८७१"},
}

def get_schemes_by_type(scheme_type: str) -> Dict[str, Dict]:
    """Get all schemes that have sub-schemes of given type (charged/voted).

    Special cases (unified schemes without subscheme selection):
    - 0029 is a voted-only scheme without explicit sub-schemes
    - 2245 is a voted-only scheme without sub-schemes (handled as whole scheme)
    - 2075 is a voted-only unified scheme (combined 20750249 + 20750294)
    """
    scheme_codes = {v["scheme"] for v in SUB_SCHEMES.values() if v["type"] == scheme_type}
    if scheme_type == "voted":
        scheme_codes.add("0029")
        scheme_codes.add("2245")
        scheme_codes.add("2075")
    return {code: info for code, info in SCHEMES.items() if code in scheme_codes}

def get_sub_schemes_by_scheme_and_type(scheme_code: str, scheme_type: str) -> Dict[str, Dict]:
    """Get sub-schemes filtered by parent scheme and type"""
    return {k: v for k, v in SUB_SCHEMES.items() 
            if v["scheme"] == scheme_code and v["type"] == scheme_type}

def get_sub_scheme_info(sub_scheme_code: str) -> Dict:
    """Get info for a specific sub-scheme"""
    return SUB_SCHEMES.get(sub_scheme_code, {})

def is_sub_scheme_implemented(sub_scheme_code: str) -> bool:
    """Check if sub-scheme is implemented - checks registry first"""
    # Check registry (new system)
    if scheme_registry.is_implemented(sub_scheme_code):
        return True
    # Fallback to static config
    info = SUB_SCHEMES.get(sub_scheme_code, {})
    return info.get("implemented", False)

def get_scheme_display_info(scheme_code: str, sub_scheme_code: str) -> Tuple[str, str, str]:
    """Get display info: (scheme_name_mr, sub_scheme_code, type_mr)"""
    scheme = SCHEMES.get(scheme_code, {})
    sub = SUB_SCHEMES.get(sub_scheme_code, {})
    # Special handling for unified schemes without sub-schemes (2245, 0029, 2075)
    if not sub and sub_scheme_code == scheme_code and scheme_code in ("2245", "0029", "2075"):
        type_mr = SCHEME_TYPES.get("voted", {}).get("mr", "दत्तमत")
    else:
        type_mr = SCHEME_TYPES.get(sub.get("type", "voted"), {}).get("mr", "दत्तमत")
    return (scheme.get("name_mr", ""), sub_scheme_code, type_mr)

def get_s2053_subschemas() -> List[str]:
    """Get all s2053 subschema codes for completion tracking"""
    return [k for k, v in SUB_SCHEMES.items() if v["scheme"] == "2053"]

