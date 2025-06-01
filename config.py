DISTRICTS = sorted(list(set(['Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar', 'Raigad', 'Ratnagiri', 'Sindhudurg'])))
CATEGORIES = sorted(list(set(['Permanent', 'Temporary'])))
CLASSES_SHEET1_2 = sorted(list(set(['Class-1 & 2', 'Class-3', 'Class-4'])))
CLASSES_SHEET3 = sorted(list(set(['1', '2', '3', '4'])))
DESIGNATIONS = sorted(list(set(['Collector', 'Additional Collector', 'Deputy Collector', 'Tehsildar/Addl. Tehsildar/Chitnis (Secretary/Clerk)', 'Naib Tehsildar', 'Accounts Officer', 'Asst. Accounts Officer', 'Deputy Accountant', 'Stenographer (Higher)', 'Stenographer (Lower)/Probationary Land Surveyor/Draftsman/Shirastedar', 'Head Clerk (Awwal Karkun)', 'Clerk', 'Vehicle Driver', 'Peon/Naik/Havaldar/Watchman/Cleaner', 'Law Officer (Honorarium)', 'Head Clerk/Deputy Accountant', 'Circle Officer', 'Clerk/Land Surveyor/Recovery Clerk', 'Telephone Operator/Steno-Typist(Law Officer Asst.)'])))
STATUSES = sorted(list(set(['Filled', 'Vacant'])))
PRIMARY_UNITS = sorted(list(set(['01- Salary', '03- Extra allowance', '06- Telephone, Electricity, Water And Charges', '10- Contractual Services', '11- Domestic Travel Expenses', '13- Office Expenses', '14- Lease And Tax', '16- Publications', '17- Computer Expenses', '20- Other Administrative Expenses', '24- Fuel Costs', '26- Advertising And Publicity Expenses', '36- Small Construction', '50- Other Expenses', '51- Motor Vehicles'])))

BUDGET_POST_DETAILS_ROW_LIMIT = 217
POST_STATUS_ROW_LIMIT = 87
POST_EXPENSES_ROW_LIMIT = 56
UNIT_EXPENDITURE_ROW_LIMIT = 104

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
POSITION_SORT_MAP = {name: i for i, name in enumerate(POSITION_ORDER)}