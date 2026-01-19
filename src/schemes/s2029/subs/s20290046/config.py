"""Configuration for sub-scheme 20290046 - District Administration (Charged)"""
from src.core.base_config import BaseSchemeConfig, FormConfig

SCHEME_CODE = "2029"
SUB_SCHEME_CODE = "20290046"

SHEET_NAMES = {
    "budget_post_details": "Page 1",
    "post_status": "Page 2",
    "post_expenses": "Page 3",
    "unit_expenditure": "Page 4",
}

SCHEME_DISTRICTS = [
    'Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar',
    'Raigad', 'Ratnagiri', 'Sindhudurg', 'DCO Staff'
]

SCHEME_DISTRICTS_MR = {
    'Mumbai City': 'मुंबई शहर',
    'Mumbai Suburban': 'मुंबई उपनगर',
    'Thane': 'ठाणे',
    'Palghar': 'पालघर',
    'Raigad': 'रायगड',
    'Ratnagiri': 'रत्नागिरी',
    'Sindhudurg': 'सिंधुदुर्ग',
    'DCO Staff': 'जिल्हा संकलक कार्यालय कर्मचारी'
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

DESIGNATIONS = [
    'Deputy Collector/Expert Officer',
    'City Architect',
    'Assistant City Architect',
    'Head Clerk',
    'Divisional Officer',
    'Clerk',
    'Vehicle Driver',
    'Notice Bearer',
    'Peon'
]

DESIGNATIONS_MR = {
    "Deputy Collector/Expert Officer": "उपसंकलक/तज्ञ अधिकारी",
    "City Architect": "शहर वास्तुविशारद",
    "Assistant City Architect": "सहाय्यक शहर वास्तुविशारद",
    "Head Clerk": "अव्वल कारकून",
    "Divisional Officer": "विभागीय अधिकारी",
    "Clerk": "लिपिक",
    "Vehicle Driver": "वाहन चालक",
    "Notice Bearer": "सूचना वाहक",
    "Peon": "शिपाई"
}

PRIMARY_UNITS = [
    '01- Salary',
    '03- Extra allowance',
    '06- Telephone, Electricity, Water And Charges',
    '11- Domestic Travel Expenses',
    '13- Office Expenses',
    '14- Lease And Tax',
    '17- Computer Expenses',
    '26- Advertising And Publicity Expenses',
    '51- Motor Vehicles'
]

PRIMARY_UNITS_MR = {
    "01- Salary": "01- वेतन",
    "03- Extra allowance": "03- अतिरिक्त भत्ता",
    "06- Telephone, Electricity, Water And Charges": "06- दूरध्वनी, वीज, पाणी शुल्क",
    "11- Domestic Travel Expenses": "11- देशांतर्गत प्रवास खर्च",
    "13- Office Expenses": "13- कार्यालयीन खर्च",
    "14- Lease And Tax": "14- भाडेपट्टी व कर",
    "17- Computer Expenses": "17- संगणक खर्च",
    "26- Advertising And Publicity Expenses": "26- जाहिरात व प्रसिद्धी खर्च",
    "51- Motor Vehicles": "51- मोटार वाहने"
}

UNIT_ACCOUNT_MAP_MR = PRIMARY_UNITS_MR

POSITION_ORDER = [
    'Deputy Collector/Expert Officer',
    'City Architect',
    'Assistant City Architect',
    'Head Clerk',
    'Divisional Officer',
    'Clerk',
    'Vehicle Driver',
    'Notice Bearer',
    'Peon'
]

MARATHI_TO_ENGLISH_DESIGNATIONS = {
    'उपसंकलक/तज्ञ अधिकारी': 'Deputy Collector/Expert Officer',
    'शहर वास्तुविशारद': 'City Architect',
    'सहाय्यक शहर वास्तुविशारद': 'Assistant City Architect',
    'अव्वल कारकून': 'Head Clerk',
    'विभागीय अधिकारी': 'Divisional Officer',
    'लिपिक': 'Clerk',
    'वाहन चालक': 'Vehicle Driver',
    'सूचना वाहक': 'Notice Bearer',
    'शिपाई': 'Peon'
}

HRA_RATE_MAP = {'X': 0.3, 'Y': 0.2, 'Z': 0.1}

CLASS_1_2_KEY = 'Class-1 & 2'
CLASS_3_KEY = 'Class-3'
CLASS_4_KEY = 'Class-4'
VALID_CLASS_KEYS = [CLASS_1_2_KEY, CLASS_3_KEY, CLASS_4_KEY]

CLASS_MAPPING = {
    CLASS_1_2_KEY: 'वर्ग-1 व 2',
    CLASS_3_KEY: 'वर्ग-3',
    CLASS_4_KEY: 'वर्ग-4'
}

CLASS_DESIGNATIONS = {
    CLASS_1_2_KEY: ['Deputy Collector/Expert Officer', 'City Architect', 'Assistant City Architect'],
    CLASS_3_KEY: ['Head Clerk', 'Divisional Officer', 'Clerk', 'Vehicle Driver'],
    CLASS_4_KEY: ['Notice Bearer', 'Peon']
}

METRICS_DB_KEYS = [
    'posts', 'salary', 'grade_pay', 'special_pay', 'dearness_allowance',
    'local_supplementary_allowance', 'house_rent_allowance', 'travel_allowance', 'other'
]

METRICS_LABELS = [
    'पदे', 'वेतन', 'ग्रेड पे', 'एकूण वेतन', 'विशेष वेतन', 'महा.भत्ता',
    'स्था.पु.भ.', 'घरभाडे', 'प्रवास भत्ता', 'इतर', 'एकूण खर्च'
]

SCHEME_CONFIG = BaseSchemeConfig(
    code=SUB_SCHEME_CODE,
    parent_scheme=SCHEME_CODE,
    scheme_type="charged",
    name_en="District Administration",
    name_mr="जिल्हा प्रशासन",
    implemented=True,
    completion_enabled=True,
    entry_point="/ui/s20290046/budget-post-details",
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
            table_name="budget_post_details_20290046",
            label_mr="प्रपत्र ड",
            label_en="Form D - Budget Post Details",
            categories=CATEGORIES,
            classes=CLASSES_SHEET1_2,
            enabled=True
        ),
        "post_status": FormConfig(
            name="post_status",
            table_name="post_status_20290046",
            label_mr="प्रपत्र क",
            label_en="Form C - Post Status",
            categories=CATEGORIES,
            classes=CLASSES_SHEET1_2,
            statuses=STATUSES,
            enabled=True
        ),
        "post_expenses": FormConfig(
            name="post_expenses",
            table_name="post_expenses_20290046",
            label_mr="प्रपत्र ब",
            label_en="Form B - Post Expenses",
            categories=CATEGORIES,
            classes=CLASSES_SHEET3,
            enabled=True
        ),
        "unit_expenditure": FormConfig(
            name="unit_expenditure",
            table_name="unit_expenditure_20290046",
            label_mr="प्रपत्र अ",
            label_en="Form A - Unit Expenditure",
            enabled=True
        )
    }
)

