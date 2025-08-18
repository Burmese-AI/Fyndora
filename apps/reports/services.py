from apps.core.services.base_services import BaseFileExporter


def export_overview_finance_report(context, exporter_class: type[BaseFileExporter]):
    table_block = {
        "type": "table",
        "columns": [
            ("title", "Title"),
            ("total_income", "Total Income"),
            ("total_expense", "Total Expense"),
            ("net_income", "Net Income"),
            ("org_share", "Org Share"),
        ],
        "rows": context["context_children"],
        "footer": [
            # Totals row
            {
                "title": "Total",
                "total_income": context["context_parent"]["total_income"],
                "total_expense": context["context_parent"]["total_expense"],
                "net_income": context["context_parent"]["net_income"],
                "org_share": context["context_parent"]["org_share"],
            },
            # Parent expenses + final profit
            {
                "title": context["context_parent"]["parent_expense_label"],
                "total_income": context["context_parent"]["parent_lvl_total_expense"],
                "total_expense": "",
                "net_income": "Final Net Profit",
                "org_share": context["context_parent"]["final_net_profit"],
            },
        ],
    }

    blocks = [
        {
            "type": "paragraph",
            "text": f"Report for {context['context_parent']['title']}",
        },
        table_block,
    ]

    exporter = exporter_class("overview-finance-report", blocks)
    return exporter.export()
