"""Configuration for sub-scheme 20290182 - District Administration (Charged)"""
from src.core.base_config import BaseSchemeConfig, FormConfig

SCHEME_CODE = "2029"
SUB_SCHEME_CODE = "20290182"

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
    'Naib Tehsildar',
    'Head Clerk (Awwal Karkun)',
    'Sub-Divisional Officer',
    'Clerical',
    'Divisional Officer',
    'Talathi',
    'Clerk',
    'Vehicle Driver',
    'Peon',
    'Mahar Keri'
]

DESIGNATIONS_MR = {
    "Deputy Collector/Expert Officer": "उप जिल्हाधिकारी/वि.मु.अधि.",
    "Naib Tehsildar": "नायब तहसिलदार",
    "Head Clerk (Awwal Karkun)": "अव्वल कारकून",
    "Sub-Divisional Officer": "उपविभागीय अधिकारी",
    "Clerical": "लिपिकीय",
    "Divisional Officer": "मंडळ अधिकारी",
    "Talathi": "तलाठी",
    "Clerk": "लिपिक",
    "Vehicle Driver": "वाहन चालक",
    "Peon": "शिपाई",
    "Mahar Keri": "महारकेरी"
}

PRIMARY_UNITS = [
    '01- Salary',
    '03- Extra allowance',
    '09- Repair of Electricity, Water and Charges',
    '11- Domestic Travel Expenses',
    '13- Office Expenses',
    '14- Lease And Tax',
    '16- Publications',
    '17- Computer Expenses',
    '24- Fuel Costs',
    '26- Advertising And Publicity Expenses'
]

PRIMARY_UNITS_MR = {
    "01- Salary": "01- वेतन",
    "03- Extra allowance": "03- अतिरिक्त भत्ता",
    "09- Repair of Electricity, Water and Charges": "09- दुरुस्तीची वोज,पाणी व शुल्क",
    "11- Domestic Travel Expenses": "11- देशांतर्गत प्रवास खर्च",
    "13- Office Expenses": "13- कार्यालयीन खर्च",
    "14- Lease And Tax": "14- भाडेपट्टी व कर",
    "16- Publications": "16- प्रकाशन",
    "17- Computer Expenses": "17- संगणक खर्च",
    "24- Fuel Costs": "24- दुधन खर्च",
    "26- Advertising And Publicity Expenses": "26- जाहिरात व प्रसिद्धी खर्च"
}

UNIT_ACCOUNT_MAP_MR = PRIMARY_UNITS_MR

POSITION_ORDER = [
    'Deputy Collector/Expert Officer',
    'Naib Tehsildar',
    'Head Clerk (Awwal Karkun)',
    'Sub-Divisional Officer',
    'Clerical',
    'Divisional Officer',
    'Talathi',
    'Clerk',
    'Vehicle Driver',
    'Peon',
    'Mahar Keri'
]

MARATHI_TO_ENGLISH_DESIGNATIONS = {
    'उप जिल्हाधिकारी/वि.मु.अधि.': 'Deputy Collector/Expert Officer',
    'उप जिल्हाधिकारी': 'Deputy Collector/Expert Officer',
    'नायब तहसिलदार': 'Naib Tehsildar',
    'अव्वल कारकून': 'Head Clerk (Awwal Karkun)',
    'उपविभागीय अधिकारी': 'Sub-Divisional Officer',
    'उपविभागीय': 'Sub-Divisional Officer',
    'लिपिकीय': 'Clerical',
    'मंडळ अधिकारी': 'Divisional Officer',
    'तलाठी': 'Talathi',
    'लिपिक': 'Clerk',
    'वाहन चालक': 'Vehicle Driver',
    'शिपाई': 'Peon',
    'महारकेरी': 'Mahar Keri'
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
    CLASS_1_2_KEY: ['Deputy Collector/Expert Officer', 'Naib Tehsildar'],
    CLASS_3_KEY: ['Head Clerk (Awwal Karkun)', 'Sub-Divisional Officer', 'Clerical', 'Divisional Officer', 'Talathi', 'Clerk', 'Vehicle Driver'],
    CLASS_4_KEY: ['Peon', 'Mahar Keri']
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
    entry_point="/ui/s20290182/budget-post-details",
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
            table_name="budget_post_details_20290182",
            label_mr="प्रपत्र ड",
            label_en="Form D - Budget Post Details",
            categories=CATEGORIES,
            classes=CLASSES_SHEET1_2,
            enabled=True
        ),
        "post_status": FormConfig(
            name="post_status",
            table_name="post_status_20290182",
            label_mr="प्रपत्र क",
            label_en="Form C - Post Status",
            categories=CATEGORIES,
            classes=CLASSES_SHEET1_2,
            statuses=STATUSES,
            enabled=True
        ),
        "post_expenses": FormConfig(
            name="post_expenses",
            table_name="post_expenses_20290182",
            label_mr="प्रपत्र ब",
            label_en="Form B - Post Expenses",
            categories=CATEGORIES,
            classes=CLASSES_SHEET3,
            enabled=True
        ),
        "unit_expenditure": FormConfig(
            name="unit_expenditure",
            table_name="unit_expenditure_20290182",
            label_mr="प्रपत्र अ",
            label_en="Form A - Unit Expenditure",
            enabled=True
        )
    }
)

