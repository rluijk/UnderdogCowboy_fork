from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.units import inch
import json
from datetime import date

# Load the conversation data
with open('/Users/reneluijk/llm_dialogs/share_david_01.json', 'r') as file:
    data = json.load(file)

# Create the PDF document
doc = SimpleDocTemplate("IFS_Therapy_Dialogue.pdf", pagesize=letter,
                        rightMargin=72, leftMargin=72,
                        topMargin=72, bottomMargin=18)

# Styles
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))

# Custom styles for therapist and client
therapist_style = ParagraphStyle(
    'Therapist',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    textColor=colors.darkblue,
    fontSize=11,
)
client_style = ParagraphStyle(
    'Client',
    parent=styles['Normal'],
    fontName='Helvetica',
    textColor=colors.darkslategray,
    fontSize=11,
)

# Content
content = []

# Title
content.append(Paragraph("IFS Therapy Dialogue Simulation", styles['Title']))
content.append(Paragraph(f"Date: {date.today().strftime('%B %d, %Y')}", styles['Normal']))
content.append(Spacer(1, 12))

# Introduction
intro_text = "This document presents a simulated dialogue between an AI IFS therapist and a client. The conversation explores internal patterns and feelings using Internal Family Systems principles."
content.append(Paragraph(intro_text, styles['Justify']))
content.append(Spacer(1, 12))

# Dialogue
for entry in data['history']:
    if entry['role'] == 'model':
        content.append(Paragraph(f"Therapist: {entry['text']}", therapist_style))
    elif entry['role'] == 'user':
        content.append(Paragraph(f"Client: {entry['text']}", client_style))
    content.append(Spacer(1, 6))

# Build the PDF
doc.build(content)

print("PDF created successfully.")