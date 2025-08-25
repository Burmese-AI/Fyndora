from apps.core.services.base_services import BaseFileExporter

def export_overview_finance_report(context, exporter_class: type[BaseFileExporter]):
    org = context["report_data"]
    rows = []

    table_block = {
        "type": "table",
        "columns": [
            ("name", "Name"),
            ("total_income", "Total Income"),
            ("total_disbursement", "Total Disbursement"),
            ("wt_net_income", "WT Net Income"),
            ("workspace_net_income", "Workspace Net Income"),
            ("org_net_income", "Org Net Income"),
            ("remittance_rate", "Remittance Rate"),
            ("expense_amount", "Expense Amount"),
            ("org_share", "Org Share"),
        ],
        "rows": rows,
    }

    def process_node(node, level="org"):
        """Recursively process org/workspace/team nodes into rows."""
        children = node.get("children", [])

        # Leaf node → team
        if not children:
            rows.append({
                "name": node["title"],
                "total_income": node["total_income"],
                "total_disbursement": node["total_expense"],
                "wt_net_income": node.get("net_income", ""),
                "workspace_net_income": "",
                "org_net_income": "",
                "remittance_rate": f"{node['remittance_rate']}%" if node.get("remittance_rate") else "-",
                "expense_amount": "-",
                "org_share": node.get("org_share", ""),
            })
            return

        # Recursive for children
        child_level = "workspace" if level == "org" else "team"
        for child in children:
            process_node(child, level=child_level)

        # Subtotal / total row
        subtotal_name = f"{node['title']} Subtotal" if level == "workspace" else f"{node['title']} Total"
        rows.append({
            "name": subtotal_name,
            "total_income": node["total_income"],
            "total_disbursement": node["total_expense"],
            "wt_net_income": node.get("net_income", "") if level == "team" else "",
            "workspace_net_income": node.get("org_share", "") if level == "workspace" else "",
            "org_net_income": node.get("org_share", "") if level == "org" else "",
            "remittance_rate": "-",
            "expense_amount": node.get("parent_lvl_total_expense", ""),
            "org_share": node.get("final_net_profit", ""),
        })

        # Blank row after subtotal for readability
        rows.append({col: "" for col, _ in table_block["columns"]})

    process_node(org, level=org.get("level", "org"))

    blocks = [
        {"type": "paragraph", "text": f"Report for {org['title']}"},
        table_block,
    ]

    exporter = exporter_class("overview-finance-report", blocks)
    return exporter.export()
