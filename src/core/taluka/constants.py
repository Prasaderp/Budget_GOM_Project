"""Reserved `taluka` column values and their fixed meaning.

These three values are the entire vocabulary of the row-role model described
in docs/plan.md section 2.2. Nothing else may write these strings into the
`taluka` column of a scoped table.
"""

# The consolidated (district-total) row. Read by every existing code path
# that has no notion of taluka scoping. Never hand-edited.
DISTRICT_LEVEL = ''

# The district office's own contribution row.
DISTRICT_OFFICE = '__district_office__'

# Values a real taluka name may never equal — enforced by the taluka
# activation path (src/utils_taluka.py) so no collision can occur.
RESERVED_TALUKA_VALUES = frozenset({DISTRICT_LEVEL, DISTRICT_OFFICE})

# Marathi display label for the district-office contribution row, used by
# the read-only breakdown page (Phase 12) and any UI that lists per-unit
# contributions alongside taluka names from src.config.DISTRICTS_MR.
DISTRICT_OFFICE_LABEL_MR = "जिल्हा कार्यालय"
