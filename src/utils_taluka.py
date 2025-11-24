from typing import List, Dict
from sqlalchemy.orm import Session
from src import models

def get_district_from_taluka_name(taluka_name: str) -> str:
    if not taluka_name:
        return ''
    if ' Taluka ' in taluka_name:
        return taluka_name.split(' Taluka ', 1)[0]
    return taluka_name

def get_possible_talukas_for_district(district: str) -> List[str]:
    from src.config import DCO_STAFF_IDENTIFIER
    if district == DCO_STAFF_IDENTIFIER:
        return []
    taluka_mapping = {
        'Mumbai City': [],
        'Mumbai Suburban': ['बोरिवली', 'अंधेरी', 'कुर्ला'],
        'Thane': ['भिवंडी', 'मुरबाड', 'ठाणे', 'कल्याण', 'अंबरनाथ', 'उल्हासनगर', 'शहापूर', 'मिरा भाईंदर'],
        'Raigad': ['अलिबाग', 'पेण', 'पनवेल', 'उरण', 'कर्जत', 'खालापूर', 'रोहा', 'मुरुड', 'सुधागड', 'महाड', 'माणगाव', 'तळा', 'म्हसळा', 'श्रीवर्धन', 'पोलादपूर', 'अपर तहसिलदार पनवेल'],
        'Palghar': ['पालघर', 'वसई', 'डहाणू', 'तलासरी', 'जव्हार', 'वाडा', 'मोखाडा', 'विक्रमगड'],
        'Ratnagiri': ['दापोली', 'खेड', 'गुहागर', 'लांजा', 'मंडणगड', 'रत्नागिरी', 'राजापूर', 'चिपळूण', 'संगमेश्वर'],
        'Sindhudurg': ['देवगड', 'कणकवली', 'मालवण', 'सावंतवाडी', 'वेंगुर्ला', 'वैभववाडी', 'कुडाळ', 'दोडामार्ग']
    }
    
    if district not in taluka_mapping:
        return []
    
    return [f"{district} Taluka {taluka_name}" for taluka_name in taluka_mapping[district]]

def get_selected_talukas(db: Session, district: str) -> List[str]:
    row = db.query(models.DistrictTalukaSelection.selected_talukas).filter(
        models.DistrictTalukaSelection.district == district
    ).first()

    if row and isinstance(row.selected_talukas, list) and row.selected_talukas:
        return row.selected_talukas

    default_talukas = get_possible_talukas_for_district(district)
    return default_talukas

def is_taluka_allowed(db: Session, taluka_name: str) -> bool:
    district = get_district_from_taluka_name(taluka_name)
    selected = get_selected_talukas(db, district)
    return taluka_name in selected

