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

        # Create PDF instance
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, f"{self.filename_prefix.title()} Export", ln=True, align="C")
        pdf.ln(10)

        # Table header
        pdf.set_font("Arial", "B", 12)
        for _, header in self.columns:
            pdf.cell(40, 10, header, border=1, align="C")
        pdf.ln()

        # Table rows
        pdf.set_font("Arial", "", 12)
        for row in self.data:
            for key, _ in self.columns:
                pdf.cell(40, 10, str(row.get(key, "")), border=1, align="C")
            pdf.ln()

        # Output PDF as HttpResponse
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write(pdf.output(dest="S").encode("latin1"))
        return response