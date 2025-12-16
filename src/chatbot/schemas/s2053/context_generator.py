"""2053-specific schema context generator - builds prompt context for 4-table structure"""
from typing import Dict, Optional
from src.core.base_config import BaseSchemeConfig

class SchemaContextGenerator:
    """Generates 2053 schema-specific context for prompts from BaseSchemeConfig"""
    
    @staticmethod
    def get_table_names(config: BaseSchemeConfig) -> Dict[str, str]:
        """Extract table names from scheme config forms (2053 structure)"""
        tables = {
            'budget_post_details': '',
            'post_status': '',
            'post_expenses': '',
            'unit_expenditure': ''
        }
        
        for form_name, form_config in config.forms.items():
            if form_name == 'budget_post_details':
                tables['budget_post_details'] = form_config.table_name
            elif form_name == 'post_status':
                tables['post_status'] = form_config.table_name
            elif form_name == 'post_expenses':
                tables['post_expenses'] = form_config.table_name
            elif form_name == 'unit_expenditure':
                tables['unit_expenditure'] = form_config.table_name
        
        return tables
    
    @staticmethod
    def generate_data_relationships(config: BaseSchemeConfig, table_names: Dict[str, str]) -> str:
        """Generate data relationships context from config (2053 structure)"""
        lines = []
        
        if table_names['budget_post_details']:
            lines.append(f"- {table_names['budget_post_details']}: Sanctioned posts, pay scales, allowances by district/category/class/designation.")
            lines.append("  * POST COUNTING: Each row represents a specific combination of (district, category, class, designation). To get total posts for a designation in a district, SUM(sanctioned_posts_2024_25 + sanctioned_posts_2025_26) across all matching rows automatically includes both Permanent/Temporary categories and all class types.")
        
        if table_names['post_status']:
            lines.append(f"- {table_names['post_status']}: Current filled/vacant status and salary data by district/category/class.")
        
        if table_names['post_expenses']:
            lines.append(f"- {table_names['post_expenses']}: Expense calculations for filled/vacant posts by district/category/class.")
            lines.append("  * CRITICAL: District-level expenses (medical_expenses, festival_advance, swagram_maharashtra_darshan, nps, seventh_pay_commission_difference) are duplicated across class types within each district - ALWAYS use MAX() not SUM() for these columns")
        
        if table_names.get('unit_expenditure'):
            lines.append(f"- {table_names['unit_expenditure']}: Multi-year expenditure tracking by district and unit account.")
            lines.append("  * COLUMNS: expenditure_2021_22, expenditure_2022_23, expenditure_2023_24, budget_2024_25, forecast_2024_25, budget_2025_26_estimating_officer, budget_2025_26_controlling_officer, budget_2025_26_admin_dept, budget_2025_26_finance_dept")
            lines.append("  * NOTE: Use \"budget_2024_25\" not \"expenditure_2024_25\" for 2024-25 data")
        
        return "\n".join(lines) if lines else "No table information available."
    
    @staticmethod
    def generate_common_patterns(config: BaseSchemeConfig, custom_context: Optional[str] = None) -> str:
        """Generate common data patterns context from config (2053 structure)"""
        lines = []
        
        if config.categories:
            cats_str = ", ".join(f"'{c}'" for c in config.categories)
            lines.append(f"- Categories: {cats_str} (case-sensitive)")
        
        if config.classes:
            classes_str = ", ".join(f"'{c}'" for c in config.classes)
            lines.append(f"- Classes: {classes_str} (use exact format from schema)")
        
        if config.designations:
            designations_str = ", ".join(f"'{d}'" for d in config.designations[:10])
            if len(config.designations) > 10:
                designations_str += f", ... ({len(config.designations)} total)"
            lines.append(f"- Designations: {designations_str}")
            if config.designations_mr:
                lines.append("  * Marathi designations map to English - use English in queries")
        
        if config.primary_units:
            units_str = ", ".join(f"'{u}'" for u in config.primary_units[:10])
            if len(config.primary_units) > 10:
                units_str += f", ... ({len(config.primary_units)} total)"
            lines.append(f"- Unit Accounts: {units_str}")
        
        lines.append("- Post Status: 'Filled', 'Vacant'")
        lines.append("- Years: 2021_22, 2022_23, 2023_24, 2024_25, 2025_26")
        
        if custom_context:
            lines.append(custom_context)
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_examples(config: BaseSchemeConfig, table_names: Dict[str, str], custom_examples: Optional[str] = None) -> str:
        """Generate example queries from config (2053 structure)"""
        if custom_examples:
            return custom_examples
        
        examples = []
        
        if table_names.get('budget_post_details'):
            bpd_alias = 'bpd'
            bpd_table = table_names['budget_post_details']
            if config.designations:
                designation = config.designations[0]
                examples.append(f"Question: What is the basic pay for {designation} in Mumbai City?")
                examples.append(f"SQL Query: SELECT {bpd_alias}.\"basic_pay\", {bpd_alias}.\"designation\", {bpd_alias}.\"district\" FROM {bpd_table} {bpd_alias} WHERE {bpd_alias}.\"district\" = 'Mumbai City' AND {bpd_alias}.\"designation\" = '{designation}' LIMIT {{top_k}};")
        
        if table_names.get('unit_expenditure'):
            ue_alias = 'ue'
            ue_table = table_names['unit_expenditure']
            if config.primary_units:
                unit = config.primary_units[0]
                examples.append("Question: Show expenditure for Palghar in 2022-23")
                examples.append(f"SQL Query: SELECT {ue_alias}.\"district\", {ue_alias}.\"unit_account\", {ue_alias}.\"expenditure_2022_23\" FROM {ue_table} {ue_alias} WHERE {ue_alias}.\"district\" = 'Palghar' AND {ue_alias}.\"unit_account\" = '{unit}' LIMIT {{top_k}};")
        
        return "\n\n".join(examples) if examples else "No examples provided."
    
    @staticmethod
    def generate_context(config: BaseSchemeConfig, custom_context: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate complete context dictionary for 2053 prompts"""
        table_names = SchemaContextGenerator.get_table_names(config)
        custom = custom_context or {}
        
        return {
            'budget_post_details_table': table_names['budget_post_details'] or 'budget_post_details_{code}',
            'post_status_table': table_names['post_status'] or 'post_status_{code}',
            'post_expenses_table': table_names['post_expenses'] or 'post_expenses_{code}',
            'unit_expenditure_table': table_names['unit_expenditure'] or 'unit_expenditure_{code}',
            'data_relationships': custom.get('data_relationships') or SchemaContextGenerator.generate_data_relationships(config, table_names),
            'common_patterns': custom.get('common_patterns') or SchemaContextGenerator.generate_common_patterns(config),
            'examples': custom.get('examples') or SchemaContextGenerator.generate_examples(config, table_names)
        }

