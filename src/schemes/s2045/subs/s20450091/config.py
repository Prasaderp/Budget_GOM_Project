"""Configuration for sub-scheme 20450091 - Stamp Duty Collection (Voted)"""
from src.core.base_config import BaseSchemeConfig, FormConfig

SCHEME_CODE = "2045"
SUB_SCHEME_CODE = "20450091"

SHEET_NAMES = {
    "budget_post_details": "Page 1",
    "post_status": "Page 2",
    "post_expenses": "Page 3",
    "unit_expenditure": "Page 4",
}


CATEGORIES = ['Permanent', 'Temporary']
CATEGORIES_MR = {"Permanent": "स्थायी", "Temporary": "अस्थायी"}

STATUSES = ['Filled', 'Vacant']
STATUSES_MR = {"Filled": "भरलेली", "Vacant": "रिक्त"}

CLASSES_SHEET1_2 = ['Class-1 & 2', 'Class-3', 'Class-4']
CLASSES_SHEET3 = ['1', '2', '3', '4']

CLASSES_MR = {
    "Class-1 & 2": "वर्ग-१ व २",
    "Class-3": "वर्ग-३",
    "Class-4": "वर्ग-४"
}

CLASSES_SHEET3_MR = {"1": "१", "2": "२", "3": "३", "4": "४"}

POST_EXPENSES_DISTRICT_COMPONENT = {
    'Mumbai City': 'SeventhPayCommissionDifferenceNPS',
    'Mumbai Suburban': 'NPS',
    'Thane': 'SeventhPayCommissionDifference',
    'Palghar': 'SeventhPayCommissionDifferenceNPS',
    'Raigad': 'NPS',
    'Ratnagiri': 'NPS',
    'Sindhudurg': 'SeventhPayCommissionDifference',
    'DCO Staff': 'NPS',
}

PERMANENT_DESIGNATIONS = [
    'Sub-District Officer',
    'Head Clerk/Awwal Karkun',
    'Cashier',
    'Clerk',
    'Peon'
]

TEMPORARY_DESIGNATIONS = [
    'Deputy Commissioner',
    'Tehsildar/Tax Collection Officer',
    'Naib Tehsildar/Asst Tax Collection Officer',
    'Stenographer (Lower Grade)',
    'Head Clerk/Awwal Karkun',
    'Inspector',
    'Clerk',
    'Vehicle Driver',
    'Peon'
]

DESIGNATIONS = list(set(PERMANENT_DESIGNATIONS + TEMPORARY_DESIGNATIONS))

DESIGNATIONS_MR = {
    "Sub-District Officer": "उपजिल्हाधिकारी",
    "Head Clerk/Awwal Karkun": "अव्वल कारकून/करसमापूक कर",
    "Cashier": "रोखपाल",
    "Clerk": "लिपिक",
    "Peon": "शिपाई",
    "Deputy Commissioner": "उप आयुक्ता",
    "Tehsildar/Tax Collection Officer": "तहसिलदार/करसमापूक कर अधिकारी",
    "Naib Tehsildar/Asst Tax Collection Officer": "ना.तह./सहा.करसमापूक कर अधिकारी",
    "Stenographer (Lower Grade)": "लघुलेखक (निम्न श्रेणी)",
    "Inspector": "निरीक्षक",
    "Vehicle Driver": "वाहन चालक"
}

PRIMARY_UNITS = [
    '01- Salary', '03- Extra allowance',
    '06- Telephone, Electricity, Water And Charges',
    '10- Contractual Services', '11- Domestic Travel Expenses',
    '13- Office Expenses', '14- Lease And Tax', '16- Publications',
    '17- Computer Expenses', '20- Other Administrative Expenses',
    '24- Fuel Costs', '26- Advertising And Publicity Expenses',
    '36- Small Construction', '50- Other Expenses', '51- Motor Vehicles'
]

PRIMARY_UNITS_MR = {
    "01- Salary": "01- वेतन",
    "03- Extra allowance": "03- अतिरिक्त भत्ता",
    "06- Telephone, Electricity, Water And Charges": "06- दूरध्वनी, वीज, पाणी शुल्क",
    "10- Contractual Services": "10- कंत्राटी सेवा",
    "11- Domestic Travel Expenses": "11- देशांतर्गत प्रवास खर्च",
    "13- Office Expenses": "13- कार्यालयीन खर्च",
    "14- Lease And Tax": "14- भाडेपट्टी व कर",
    "16- Publications": "16- प्रकाशने",
    "17- Computer Expenses": "17- संगणक खर्च",
    "20- Other Administrative Expenses": "20- इतर प्रशासकीय खर्च",
    "24- Fuel Costs": "24- इंधन खर्च",
    "26- Advertising And Publicity Expenses": "26- जाहिरात व प्रसिद्धी खर्च",
    "36- Small Construction": "36- लहान बांधकाम",
    "50- Other Expenses": "50- इतर खर्च",
    "51- Motor Vehicles": "51- मोटार वाहने"
}

UNIT_ACCOUNT_MAP_MR = PRIMARY_UNITS_MR

POSITION_ORDER = DESIGNATIONS

MARATHI_TO_ENGLISH_DESIGNATIONS = {
    'उपजिल्हाधिकारी': 'Sub-District Officer',
    'अव्वल कारकून/करसमापूक कर': 'Head Clerk/Awwal Karkun',
    'रोखपाल': 'Cashier',
    'लिपिक': 'Clerk',
    'शिपाई': 'Peon',
    'उप आयुक्ता': 'Deputy Commissioner',
    'तहसिलदार/करसमापूक कर अधिकारी': 'Tehsildar/Tax Collection Officer',
    'ना.तह./सहा.करसमापूक कर अधिकारी': 'Naib Tehsildar/Asst Tax Collection Officer',
    'लघुलेखक (निम्न श्रेणी)': 'Stenographer (Lower Grade)',
    'लघुलेखक': 'Stenographer (Lower Grade)',
    'निरीक्षक': 'Inspector',
    'वाहन चालक': 'Vehicle Driver'
}

HRA_RATE_MAP = {'X': 0.3, 'Y': 0.2, 'Z': 0.1}

# Import shared constants instead of duplicating
from src.schemes.s2045.common.utils.constants import (
    CLASS_1_2_KEY, CLASS_3_KEY, CLASS_4_KEY, VALID_CLASS_KEYS,
    CLASS_MAPPING, METRICS_DB_KEYS, METRICS_LABELS
)

CLASS_DESIGNATIONS = {
    CLASS_1_2_KEY: ['Sub-District Officer', 'Deputy Commissioner', 'Tehsildar/Tax Collection Officer', 'Naib Tehsildar/Asst Tax Collection Officer'],
    CLASS_3_KEY: ['Stenographer (Lower Grade)', 'Head Clerk/Awwal Karkun', 'Cashier', 'Inspector', 'Clerk', 'Vehicle Driver'],
    CLASS_4_KEY: ['Peon']
}

SCHEME_CONFIG = BaseSchemeConfig(
    code=SUB_SCHEME_CODE,
    parent_scheme=SCHEME_CODE,
    scheme_type="voted",
    name_en="Stamp Duty Collection",
    name_mr="मुद्रांक शुल्क संकलन",
    implemented=True,
    completion_enabled=True,
    entry_point="/ui/s20450091/budget-post-details",
    designations=DESIGNATIONS,
    designations_mr=DESIGNATIONS_MR,
    categories=CATEGORIES,
    categories_mr=CATEGORIES_MR,
    classes=CLASSES_SHEET1_2,
    classes_mr=CLASSES_MR,
    primary_units=PRIMARY_UNITS,
    primary_units_mr=PRIMARY_UNITS_MR,
    forms={
        "budget_post_details": FormConfig(
            name="budget_post_details",
            table_name="budget_post_details_20450091",
            label_mr="प्रपत्र ड",
            label_en="Form D - Budget Post Details",
            categories=CATEGORIES,
            classes=CLASSES_SHEET1_2,
            enabled=True
        ),
        "post_status": FormConfig(
            name="post_status",
            table_name="post_status_20450091",
            label_mr="प्रपत्र क",
            label_en="Form C - Post Status",
            categories=CATEGORIES,
            classes=CLASSES_SHEET1_2,
            statuses=STATUSES,
            enabled=True
        ),
        "post_expenses": FormConfig(
            name="post_expenses",
            table_name="post_expenses_20450091",
            label_mr="प्रपत्र ब",
            label_en="Form B - Post Expenses",
            categories=CATEGORIES,
            classes=CLASSES_SHEET3,
            enabled=True
        ),
        "unit_expenditure": FormConfig(
            name="unit_expenditure",
            table_name="unit_expenditure_20450091",
            label_mr="प्रपत्र अ",
            label_en="Form A - Unit Expenditure",
            enabled=True
        )
    }
)

