from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, TableStyle, Table
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.units import inch
from datetime import datetime
import re
import logging
import os
from textwrap import wrap

class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.styles.add(ParagraphStyle(
            name='ArticleTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.black
        ))
        self.styles.add(ParagraphStyle(
            name='ArticleInfo',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.gray
        ))
        self.styles.add(ParagraphStyle(
            name='UserText',
            parent=self.styles['BodyText'],
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.black,
            spaceAfter=6
        ))
        self.styles.add(ParagraphStyle(
            name='ModelText',
            parent=self.styles['BodyText'],
            fontName='Times-Roman',
            fontSize=9,
            textColor=colors.black,
            spaceAfter=6
        ))
        self.styles.add(ParagraphStyle(
            name='UserHeader',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=colors.black,
            spaceAfter=6,
            alignment=TA_LEFT
        ))
        self.styles.add(ParagraphStyle(
            name='ModelHeader',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=colors.black,
            spaceAfter=6,
            alignment=TA_LEFT
        ))

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.image_path = os.path.join(self.base_dir, 'images', 'uc-stamp.png')
        self.image_path = os.path.abspath(self.image_path)

    def clean_text(self, text):
        text = re.sub(r'[<>&]', '', text)
        return text

    def wrap_text(self, text, width=60):
        return '\n'.join(wrap(text, width))

    def generate_pdf(self, output_path, title, dialogue_data, filename):
        doc = SimpleDocTemplate(output_path, pagesize=letter,
                                rightMargin=0.5*inch, leftMargin=0.5*inch,
                                topMargin=0.5*inch, bottomMargin=0.5*inch)

        content = []

        # Header
        if os.path.exists(self.image_path):
            try:
                logo = Image(self.image_path, width=85, height=85)
            except Exception as e:
                logging.error(f"Error loading image from {self.image_path}: {e}")
                logo = Paragraph("UC", self.styles['Normal'])
        else:
            logging.warning(f"Image file not found at {self.image_path}")
            logo = Paragraph("UC", self.styles['Normal'])

        header_data = [
            [logo, 
             Paragraph("Printout by Underdog Cowboy", self.styles['Normal']),
             Paragraph(datetime.now().strftime("%B %d, %Y"), self.styles['Normal'])]
        ]
        header_table = Table(header_data, colWidths=[2*inch, 3*inch, 2*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        content.append(header_table)
        content.append(Spacer(1, 0.25*inch))

        # Title
        content.append(Paragraph(title, self.styles['ArticleTitle']))
        
        # Article info
        content.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y %I:%M %p')}", self.styles['ArticleInfo']))
        content.append(Spacer(1, 0.25*inch))

        # Two-column dialogue
        for i, entry in enumerate(dialogue_data, start=1):
            try:
                role = entry['role']
                text = self.clean_text(entry['text'])
                wrapped_text = self.wrap_text(text)
                if role == 'user':
                    content.append(
                        Table([
                            [Paragraph(f"{i}. User", self.styles['UserHeader']), ""],
                            [Paragraph(wrapped_text, self.styles['UserText']), ""]
                        ],
                        colWidths=[3.4*inch, 3.6*inch],
                        style=self.get_table_style())
                    )
                elif role == 'model':
                    content.append(
                        Table([
                            ["", Paragraph(f"{i}. Model", self.styles['ModelHeader'])],
                            ["", Paragraph(wrapped_text, self.styles['ModelText'])]
                        ],
                        colWidths=[3.6*inch, 3.4*inch],
                        style=self.get_table_style())
                    )
            except Exception as e:
                logging.error(f"Error processing dialogue entry {i}: {e}")

        # Build the PDF
        doc.build(content)

        print(f"PDF exported successfully to {output_path}")

    def get_table_style(self):
        return TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (0, -1), 0),
            ('RIGHTPADDING', (0, 0), (0, -1), 12),
            ('LEFTPADDING', (1, 0), (1, -1), 12),
            ('RIGHTPADDING', (1, 0), (1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LINEAFTER', (0, 0), (0, -1), 0.5, colors.grey),
        ])