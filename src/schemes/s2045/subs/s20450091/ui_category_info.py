from src.schemes.s2045.common.handlers.base_category_info_handler import create_category_info_router
from .models import PostExpenses

router = create_category_info_router(
    prefix="/ui/s20450091/category-wise-info",
    post_expenses_model=PostExpenses,
    template_path="schemes/s2045/subs/s20450091/category_wise_info.html"
)
