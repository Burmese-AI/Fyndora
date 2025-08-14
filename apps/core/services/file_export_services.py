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
        writer.writerow([header for _, header in self.columns])
        for row in self.data:
            writer.writerow([row.get(key, "") for key, _ in self.columns])

        return response


class PdfExporter(BaseFileExporter):
    def export(self):
        filename = f"{self.filename_prefix}-{datetime.now().date()}.pdf"

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, f"{self.filename_prefix.title()} Export", ln=True, align="C")
        pdf.ln(10)

        # --- Calculate dynamic column widths ---
        pdf.set_font("Arial", "", 8)
        col_widths = []
        for key, header in self.columns:
            # start with header width
            max_width = pdf.get_string_width(str(header)) + 6
            for row in self.data:
                text_width = pdf.get_string_width(str(row.get(key, ""))) + 6
                if text_width > max_width:
                    max_width = text_width
            col_widths.append(max_width)

        # scale if too wide for page
        table_width = sum(col_widths)
        page_width = pdf.w - 2 * pdf.l_margin
        if table_width > page_width:
            scale = page_width / table_width
            col_widths = [w * scale for w in col_widths]

        # --- Table header ---
        pdf.set_font("Arial", "B", 8)
        for (key, header), width in zip(self.columns, col_widths):
            pdf.cell(width, 10, str(header), border=1, align="C")
        pdf.ln()

        # --- Table rows ---
        pdf.set_font("Arial", "", 8)
        for row in self.data:
            for (key, _), width in zip(self.columns, col_widths):
                pdf.cell(width, 10, str(row.get(key, "")), border=1, align="C")
            pdf.ln()

        # Output
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write(pdf.output(dest="S").encode("latin1"))
        return response
