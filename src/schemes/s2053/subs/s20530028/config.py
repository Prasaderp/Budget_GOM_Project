"""Configuration for sub-scheme 20530028 - District Administration (Voted)"""
from src.core.base_config import BaseSchemeConfig, FormConfig

SCHEME_CODE = "2053"
SUB_SCHEME_CODE = "20530028"

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
    'Collector', 'Additional Collector', 'Deputy Collector',
    'Tehsildar/Addl. Tehsildar/Chitnis (Secretary/Clerk)',
    'Naib Tehsildar', 'Accounts Officer', 'Asst. Accounts Officer',
    'Deputy Accountant', 'Stenographer (Higher)',
    'Stenographer (Lower)/Probationary Land Surveyor/Draftsman/Shirastedar',
    'Head Clerk (Awwal Karkun)', 'Clerk', 'Vehicle Driver',
    'Peon/Naik/Havaldar/Watchman/Cleaner', 'Law Officer (Honorarium)',
    'Head Clerk/Deputy Accountant', 'Circle Officer',
    'Clerk/Land Surveyor/Recovery Clerk',
    'Telephone Operator/Steno-Typist(Law Officer Asst.)'
]

DESIGNATIONS_MR = {
    "Collector": "जिल्हाधिकारी",
    "Additional Collector": "अपर जिल्हाधिकारी",
    "Deputy Collector": "उपजिल्हाधिकारी",
    "Tehsildar/Addl. Tehsildar/Chitnis (Secretary/Clerk)": "तहसिलदार/अप्पर तहसिलदार/चिटणीस",
    "Naib Tehsildar": "नायब तहसिलदार",
    "Accounts Officer": "लेखाधिकारी",
    "Asst. Accounts Officer": "सहा. लेखाधिकारी",
    "Deputy Accountant": "उपलेखापाल",
    "Stenographer (Higher)": "लघुलेखक (उच्च)",
    "Stenographer (Lower)/Probationary Land Surveyor/Draftsman/Shirastedar": "लघुलेखक(निम्न)/परिक्षण भूमापक/आरेखक/शिरस्तेदार",
    "Head Clerk (Awwal Karkun)": "अव्वल कारकून",
    "Clerk": "लिपिक",
    "Vehicle Driver": "वाहन चालक",
    "Peon/Naik/Havaldar/Watchman/Cleaner": "शिपाई/नाईक/हवालदार/वॉचमन/स्वच्छक",
    "Law Officer (Honorarium)": "विधी अधिकारी (मानधन)",
    "Head Clerk/Deputy Accountant": "अव्वल कारकून/उपलेखापाल",
    "Circle Officer": "मंडळ अधिकारी",
    "Clerk/Land Surveyor/Recovery Clerk": "लिपिक/भूमापक/वसूली कारकून",
    "Telephone Operator/Steno-Typist(Law Officer Asst.)": "टेलि.ऑपरेटर/लघुटंकलेखक(विधी अधि.सहा.)",
    "Deputy Collector / Probationary Deputy Collector": "उपजिल्हाधिकारी/परिविक्षाधीन उपजिल्हाधिकारी",
    "Tehsildar/Additional Tehsildar/Chitnis (Clerk/Secretary)/Probationary Tehsildar": "तहसिलदार/अप्पर तहसिलदार/चिटणीस/परिविक्षाधीन तहसिलदार",
    "Naib Tehsildar/Probationary Naib Tehsildar": "नायब तहसिलदार/परिविक्षाधीन ना.तहसिलदार"
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

POSITION_ORDER = [
    'Collector', 'Additional Collector', 'Deputy Collector',
    'Deputy Collector / Probationary Deputy Collector',
    'Tehsildar/Addl. Tehsildar/Chitnis (Secretary/Clerk)',
    'Tehsildar/Additional Tehsildar/Chitnis (Clerk/Secretary)/Probationary Tehsildar',
    'Naib Tehsildar', 'Naib Tehsildar/Probationary Naib Tehsildar',
    'Accounts Officer', 'Asst. Accounts Officer', 'Law Officer (Honorarium)',
    'Deputy Accountant', 'Head Clerk/Deputy Accountant', 'Head Clerk (Awwal Karkun)',
    'Circle Officer', 'Stenographer (Higher)', 'Clerk',
    'Clerk/Land Surveyor/Recovery Clerk',
    'Stenographer (Lower)/Probationary Land Surveyor/Draftsman/Shirastedar',
    'Vehicle Driver', 'Telephone Operator/Steno-Typist(Law Officer Asst.)',
    'Peon/Naik/Havaldar/Watchman/Cleaner'
]

MARATHI_TO_ENGLISH_DESIGNATIONS = {
    'जिल्हाधिकारी': 'Collector',
    'कलेक्टर': 'Collector',
    'अपर जिल्हाधिकारी': 'Additional Collector',
    'अप्पर जिल्हाधिकारी': 'Additional Collector',
    'उपजिल्हाधिकारी': 'Deputy Collector',
    'तहसिलदार': 'Tehsildar',
    'नायब तहसिलदार': 'Naib Tehsildar',
    'लेखाधिकारी': 'Accounts Officer',
    'सहा. लेखाधिकारी': 'Asst. Accounts Officer',
    'उपलेखापाल': 'Deputy Accountant',
    'लघुलेखक': 'Stenographer',
    'लघुलेखक (उच्च)': 'Stenographer (Higher)',
    'अव्वल कारकून': 'Head Clerk (Awwal Karkun)',
    'लिपिक': 'Clerk',
    'वाहन चालक': 'Vehicle Driver',
    'शिपाई': 'Peon/Naik/Havaldar/Watchman/Cleaner',
    'विधी अधिकारी': 'Law Officer (Honorarium)',
    'मंडळ अधिकारी': 'Circle Officer',
}

SCHEME_CONFIG = BaseSchemeConfig(
    code=SUB_SCHEME_CODE,
    parent_scheme=SCHEME_CODE,
    scheme_type="voted",
    name_en="District Administration",
    name_mr="जिल्हा प्रशासन",
    implemented=True,
    entry_point="/ui/s20530028/budget-post-details",
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
            table_name="budget_post_details",
            label_mr="प्रपत्र ड",
            label_en="Form D - Budget Post Details",
            categories=CATEGORIES,
            classes=CLASSES_SHEET1_2,
            enabled=True
        ),
        "post_status": FormConfig(
            name="post_status",
            table_name="post_status",
            label_mr="प्रपत्र क",
            label_en="Form C - Post Status",
            categories=CATEGORIES,
            classes=CLASSES_SHEET1_2,
            statuses=STATUSES,
            enabled=True
        ),
        "post_expenses": FormConfig(
            name="post_expenses",
            table_name="post_expenses",
            label_mr="प्रपत्र ब",
            label_en="Form B - Post Expenses",
            categories=CATEGORIES,
            classes=CLASSES_SHEET3,
            enabled=True
        ),
        "unit_expenditure": FormConfig(
            name="unit_expenditure",
            table_name="unit_expenditure",
            label_mr="प्रपत्र अ",
            label_en="Form A - Unit Expenditure",
            enabled=True
        )
    }
)

