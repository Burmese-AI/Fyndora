import csv
from datetime import datetime
from fpdf import FPDF

from django.http import HttpResponse

from .base_services import BaseFileExporter


class CsvExporter(BaseFileExporter):
    def export(self):
        filename = f"{self.filename_prefix}-{datetime.now().date()}.csv"
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)

        for block in self.blocks:
            if block["type"] == "table":
                writer.writerow([header for _, header in block["columns"]])
                for row in block["rows"]:
                    writer.writerow([row.get(key, "") for key, _ in block["columns"]])
                if "footer" in block:
                    for footer_row in block["footer"]:
                        writer.writerow(
                            [footer_row.get(key, "") for key, _ in block["columns"]]
                        )
            elif block["type"] == "paragraph":
                writer.writerow([block["text"]])

        return response


class PdfExporter(BaseFileExporter):
    def export(self):
        filename = f"{self.filename_prefix}-{datetime.now().date()}.pdf"

        pdf = FPDF()
        pdf.add_page()

        for block in self.blocks:
            if block["type"] == "table":
                col_widths = self._calculate_col_widths(
                    pdf, block["columns"], block["rows"], block.get("footer", [])
                )

                pdf.set_font("Arial", "B", 8)
                for (_, header), width in zip(block["columns"], col_widths):
                    pdf.cell(width, 8, str(header), border=1, align="C")
                pdf.ln()

                pdf.set_font("Arial", "", 8)
                for row in block["rows"]:
                    for (key, _), width in zip(block["columns"], col_widths):
                        pdf.cell(width, 8, str(row.get(key, "")), border=1, align="C")
                    pdf.ln()

                if "footer" in block:
                    pdf.set_font("Arial", "B", 8)
                    for footer_row in block["footer"]:
                        for (key, _), width in zip(block["columns"], col_widths):
                            pdf.cell(
                                width,
                                8,
                                str(footer_row.get(key, "")),
                                border=1,
                                align="C",
                            )
                        pdf.ln()

                pdf.ln(5)

            elif block["type"] == "paragraph":
                pdf.set_font("Arial", "", 10)
                pdf.multi_cell(0, 8, block["text"])
                pdf.ln(5)

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write(pdf.output(dest="S").encode("latin1"))
        return response

    def _calculate_col_widths(self, pdf, columns, rows, footer_rows):
        pdf.set_font("Arial", "", 8)
        col_widths = []
        all_rows = rows + footer_rows
        for key, header in columns:
            max_width = pdf.get_string_width(str(header)) + 6
            for row in all_rows:
                text_width = pdf.get_string_width(str(row.get(key, ""))) + 6
                if text_width > max_width:
                    max_width = text_width
            col_widths.append(max_width)
        page_width = pdf.w - 2 * pdf.l_margin
        if sum(col_widths) > page_width:
            scale = page_width / sum(col_widths)
            col_widths = [w * scale for w in col_widths]
        return col_widths
