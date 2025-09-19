from io import BytesIO
import csv
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from django.utils import timezone


def generate_pdf(report):
    """Generate PDF report using ReportLab"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.darkblue
    )
    
    # Title
    elements.append(Paragraph("Interview Proctoring Report", title_style))
    elements.append(Spacer(1, 20))
    
    # Report details
    elements.append(Paragraph("Report Details", heading_style))
    
    report_data = [
        ['Candidate Name:', report.candidate_name],
        ['Interview Date:', report.interview.start_time.strftime('%Y-%m-%d %H:%M')],
        ['Duration:', str(report.total_duration) if report.total_duration else 'N/A'],
        ['Generated At:', report.generated_at.strftime('%Y-%m-%d %H:%M')],
        ['Integrity Score:', f"{report.integrity_score}/100"],
    ]
    
    report_table = Table(report_data, colWidths=[2*inch, 4*inch])
    report_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.beige),
    ]))
    
    elements.append(report_table)
    elements.append(Spacer(1, 20))
    
    # Detection Summary
    elements.append(Paragraph("Detection Summary", heading_style))
    
    detection_data = [
        ['Event Type', 'Count'],
        ['Focus Lost Events', str(report.focus_lost_events)],
        ['No Face Detected', str(report.no_face_events)],
        ['Multiple Faces', str(report.multiple_faces_events)],
        ['Phone Detected', str(report.phone_detected_events)],
        ['Notes Detected', str(report.notes_detected_events)],
        ['Device Detected', str(report.device_detected_events)],
        ['Drowsiness Detected', str(report.drowsiness_events)],
        ['Audio Anomalies', str(report.audio_anomaly_events)],
    ]
    
    detection_table = Table(detection_data, colWidths=[3*inch, 2*inch])
    detection_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(detection_table)
    elements.append(Spacer(1, 20))
    
    # Integrity Score Analysis
    elements.append(Paragraph("Integrity Score Analysis", heading_style))
    
    if report.integrity_score >= 90:
        score_color = colors.green
        score_text = "Excellent"
    elif report.integrity_score >= 70:
        score_color = colors.orange
        score_text = "Good"
    elif report.integrity_score >= 50:
        score_color = colors.red
        score_text = "Fair"
    else:
        score_color = colors.darkred
        score_text = "Poor"
    
    score_style = ParagraphStyle(
        'ScoreStyle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=score_color,
        alignment=TA_CENTER
    )
    
    elements.append(Paragraph(f"Overall Integrity Score: {report.integrity_score}/100", score_style))
    elements.append(Paragraph(f"Assessment: {score_text}", score_style))
    elements.append(Spacer(1, 20))
    
    # Recommendations
    elements.append(Paragraph("Recommendations", heading_style))
    
    recommendations = []
    if report.focus_lost_events > 5:
        recommendations.append("• High number of focus lost events detected. Consider improving attention during interviews.")
    
    if report.phone_detected_events > 0:
        recommendations.append("• Phone usage detected during interview. Ensure no external devices are used.")
    
    if report.notes_detected_events > 0:
        recommendations.append("• Notes or materials detected. Ensure interview is conducted without external aids.")
    
    if report.multiple_faces_events > 0:
        recommendations.append("• Multiple faces detected. Ensure only the candidate is present during the interview.")
    
    if not recommendations:
        recommendations.append("• No significant issues detected. Interview conducted with good integrity.")
    
    for rec in recommendations:
        elements.append(Paragraph(rec, styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def generate_csv(report):
    """Generate CSV report"""
    output = BytesIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Field', 'Value'])
    
    # Write report data
    writer.writerow(['Candidate Name', report.candidate_name])
    writer.writerow(['Interview Date', report.interview.start_time.strftime('%Y-%m-%d %H:%M')])
    writer.writerow(['Duration', str(report.total_duration) if report.total_duration else 'N/A'])
    writer.writerow(['Generated At', report.generated_at.strftime('%Y-%m-%d %H:%M')])
    writer.writerow(['Integrity Score', report.integrity_score])
    writer.writerow(['', ''])  # Empty row
    
    writer.writerow(['Detection Events', 'Count'])
    writer.writerow(['Focus Lost Events', report.focus_lost_events])
    writer.writerow(['No Face Detected', report.no_face_events])
    writer.writerow(['Multiple Faces', report.multiple_faces_events])
    writer.writerow(['Phone Detected', report.phone_detected_events])
    writer.writerow(['Notes Detected', report.notes_detected_events])
    writer.writerow(['Device Detected', report.device_detected_events])
    writer.writerow(['Drowsiness Detected', report.drowsiness_events])
    writer.writerow(['Audio Anomalies', report.audio_anomaly_events])
    writer.writerow(['', ''])  # Empty row
    
    writer.writerow(['Additional Metrics', 'Value'])
    writer.writerow(['Face Detection Accuracy', report.face_detection_accuracy])
    writer.writerow(['Audio Quality Score', report.audio_quality_score])
    writer.writerow(['Total Suspicious Events', report.suspicious_events])
    writer.writerow(['Total Focus Loss Count', report.focus_loss_count])
    
    output.seek(0)
    return output.getvalue()
