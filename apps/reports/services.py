from apps.core.services.base_services import BaseFileExporter

def export_overview_finance_report(context, exporter_class: type[BaseFileExporter]):
    columns = [
        ("title", "Title"),
        ("total_income", "Total Income"),
        ("total_expense", "Total Expense"),
        ("net_income", "Net Income"),
        ("org_share", "Org Share"),
        ("parent_lvl_total_expense", "Parent Level Expenses"),
        ("final_net_profit", "Final Net Profit"),
    ]
    data = context["context_children"] + [context["context_parent"]]
    exporter = exporter_class("overview-finance-report", columns, data)
    return exporter.export()