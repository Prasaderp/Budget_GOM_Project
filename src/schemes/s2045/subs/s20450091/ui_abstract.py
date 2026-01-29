from src.schemes.s2045.common.handlers.base_abstract_handler import create_abstract_router
from .models import UnitExpenditure
from .config import UNIT_ACCOUNT_MAP_MR

router = create_abstract_router(
    prefix="/ui/s20450091/district-wise-abstract",
    model_class=UnitExpenditure,
    unit_account_map=UNIT_ACCOUNT_MAP_MR,
    template_path="schemes/s2045/subs/s20450091/district_wise_abstract.html",
    fiscal_year_field='budget_2025_26_estimating_officer',
    expenditure_field='expenditure_2023_24',
    current_budget_field='budget_2024_25',
    forecast_field='forecast_2024_25'
)




