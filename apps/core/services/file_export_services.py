from django.http import HttpResponse
import csv
from datetime import datetime
# from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
# from reportlab.lib import colors
# from reportlab.lib.styles import getSampleStyleSheet
# from reportlab.lib.pagesizes import A4
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
    
# class PdfExporter(BaseExporter):
#     def export(self):
#         filename = f"{self.filename_prefix}-{datetime.now().date()}.pdf"
#         response = HttpResponse(content_type="application/pdf")
#         response["Content-Disposition"] = f'attachment; filename="{filename}"'

#         doc = SimpleDocTemplate(response, pagesize=A4)
#         styles = getSampleStyleSheet()
#         elements = [
#             Paragraph(f"{self.filename_prefix.title()} Export", styles["Title"]),
#             Spacer(1, 12)
#         ]

#         table_data = [[header for _, header in self.columns]]
#         for row in self.data:
#             table_data.append([str(row.get(key, "")) for key, _ in self.columns])

#         table = Table(table_data)
#         table.setStyle(TableStyle([
#             ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
#             ("GRID", (0, 0), (-1, -1), 1, colors.black),
#             ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
#             ("ALIGN", (0, 0), (-1, -1), "CENTER"),
#         ]))

#         elements.append(table)
#         doc.build(elements)

#         return response