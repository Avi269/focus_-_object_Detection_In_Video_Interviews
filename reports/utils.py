from io import BytesIO
import csv
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def generate_pdf(report):
    """Generate PDF report using ReportLab with enhanced error handling"""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            rightMargin=72, 
            leftMargin=72, 
            topMargin=72, 
            bottomMargin=18,
            title=f"Interview Report - {report.candidate_name}",
            author="Proctoring System"
        )
        
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
            textColor=colors.HexColor('#0d6efd'),
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#0d6efd'),
            fontName='Helvetica-Bold'
        )
        
        subheading_style = ParagraphStyle(
            'SubHeading',
            parent=styles['Heading3'],
            fontSize=14,
            spaceAfter=10,
            textColor=colors.HexColor('#6c757d'),
            fontName='Helvetica-Bold'
        )
        
        # Add logo/header (if you have one)
        # elements.append(Image('path/to/logo.png', width=2*inch, height=1*inch))
        
        # Title
        elements.append(Paragraph("📊 Interview Proctoring Report", title_style))
        elements.append(Spacer(1, 12))
        
        # Timestamp watermark
        timestamp_style = ParagraphStyle(
            'Timestamp',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        elements.append(Paragraph(
            f"Generated on {timezone.now().strftime('%B %d, %Y at %I:%M %p')}",

            timestamp_style
        ))
        elements.append(Spacer(1, 20))
        
        # Report details section
        elements.append(Paragraph("📋 Report Details", heading_style))
        
        # Format interview date
        interview_date = "N/A"
        if report.interview.start_time:
            interview_date = report.interview.start_time.strftime('%B %d, %Y at %I:%M %p')
        
        # Format duration
        duration_str = "N/A"
        if report.total_duration:
            total_seconds = int(report.total_duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            if hours > 0:
                duration_str = f"{hours}h {minutes}m"
            else:
                duration_str = f"{minutes}m"
        
        # Determine integrity grade and color
        score = report.integrity_score
        if score >= 90:
            grade = "A - Excellent"
            grade_color = colors.green
        elif score >= 80:
            grade = "B - Good"
            grade_color = colors.blue
        elif score >= 70:
            grade = "C - Fair"
            grade_color = colors.orange
        elif score >= 60:
            grade = "D - Poor"
            grade_color = colors.orangered
        else:
            grade = "F - Critical"
            grade_color = colors.red
        
        report_data = [
            ['Candidate Name:', report.candidate_name],
            ['Interview Title:', report.interview.title],
            ['Interview Date:', interview_date],
            ['Duration:', duration_str],
            ['Report Generated:', report.generated_at.strftime('%B %d, %Y at %I:%M %p')],
            ['Integrity Score:', f"{report.integrity_score}/100 - {grade}"],
        ]
        
        report_table = Table(report_data, colWidths=[2.5*inch, 3.5*inch])
        report_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(report_table)
        elements.append(Spacer(1, 25))
        
        # Integrity Score Visual
        elements.append(Paragraph("🎯 Integrity Score Analysis", heading_style))
        
        score_visual_data = [
            ['Score', 'Grade', 'Assessment'],
            [str(report.integrity_score), grade.split(' - ')[0], grade.split(' - ')[1]]
        ]
        
        score_table = Table(score_visual_data, colWidths=[1.5*inch, 1.5*inch, 3*inch])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (1, 1), (1, 1), grade_color),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(score_table)
        elements.append(Spacer(1, 25))
        
        # Detection Summary with categorization
        elements.append(Paragraph("🔍 Detection Summary", heading_style))
        
        # Categorize events by severity
        high_severity_count = (
            report.multiple_faces_events + 
            report.phone_detected_events + 
            report.notes_detected_events + 
            report.device_detected_events
        )
        
        medium_severity_count = (
            report.focus_lost_events + 
            report.no_face_events + 
            report.drowsiness_events
        )
        
        low_severity_count = report.audio_anomaly_events
        
        detection_data = [
            ['Event Type', 'Count', 'Severity'],
            ['Focus Lost Events', str(report.focus_lost_events), 'Medium'],
            ['No Face Detected', str(report.no_face_events), 'Medium'],
            ['Multiple Faces', str(report.multiple_faces_events), 'High'],
            ['Phone Detected', str(report.phone_detected_events), 'High'],
            ['Notes Detected', str(report.notes_detected_events), 'High'],
            ['Device Detected', str(report.device_detected_events), 'High'],
            ['Drowsiness Detected', str(report.drowsiness_events), 'Medium'],
            ['Audio Anomalies', str(report.audio_anomaly_events), 'Low'],
            ['', '', ''],
            ['High Severity Total', str(high_severity_count), ''],
            ['Medium Severity Total', str(medium_severity_count), ''],
            ['Low Severity Total', str(low_severity_count), ''],
        ]
        
        detection_table = Table(detection_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
        
        # Apply conditional coloring based on severity
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 1), (-1, 8), colors.white),
            ('GRID', (0, 0), (-1, 8), 0.5, colors.grey),
            ('LINEABOVE', (0, 9), (-1, 9), 2, colors.black),
            ('BACKGROUND', (0, 9), (-1, -1), colors.HexColor('#f8f9fa')),
            ('FONTNAME', (0, 9), (0, -1), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        
        # Color-code severity levels
        for i, row in enumerate(detection_data[1:9], start=1):
            if 'High' in row[2]:
                table_style.append(('TEXTCOLOR', (2, i), (2, i), colors.red))
            elif 'Medium' in row[2]:
                table_style.append(('TEXTCOLOR', (2, i), (2, i), colors.orange))
            elif 'Low' in row[2]:
                table_style.append(('TEXTCOLOR', (2, i), (2, i), colors.green))
        
        detection_table.setStyle(TableStyle(table_style))
        
        elements.append(detection_table)
        elements.append(Spacer(1, 25))
        
        # Quality Metrics
        elements.append(Paragraph("📈 Quality Metrics", heading_style))
        
        quality_data = [
            ['Metric', 'Score'],
            ['Face Detection Accuracy', f"{report.face_detection_accuracy:.2%}"],
            ['Audio Quality Score', f"{report.audio_quality_score:.2%}"],
        ]
        
        quality_table = Table(quality_data, colWidths=[3*inch, 3*inch])
        quality_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(quality_table)
        elements.append(Spacer(1, 25))
        
        # Recommendations
        elements.append(Paragraph("💡 Recommendations & Assessment", heading_style))
        
        recommendations = []
        
        if high_severity_count > 0:
            recommendations.append(
                "⚠️ <b>Critical Issues Detected:</b> Multiple high-severity violations were recorded. "
                "Interview integrity is significantly compromised."
            )
        
        if report.focus_lost_events > 5:
            recommendations.append(
                "• <b>Attention Concerns:</b> High number of focus lost events detected. "
                "Candidate showed difficulty maintaining attention during the interview."
            )
        
        if report.phone_detected_events > 0:
            recommendations.append(
                "• <b>Device Usage:</b> Phone usage detected during interview. "
                "Ensure no external devices are accessible during future interviews."
            )
        
        if report.notes_detected_events > 0:
            recommendations.append(
                "• <b>Unauthorized Materials:</b> Notes or materials detected. "
                "Interview should be conducted without external aids."
            )
        
        if report.multiple_faces_events > 0:
            recommendations.append(
                "• <b>Multiple Participants:</b> Additional people detected in frame. "
                "Ensure only the candidate is present during interviews."
            )
        
        if report.drowsiness_events > 3:
            recommendations.append(
                "• <b>Fatigue Indicators:</b> Signs of drowsiness detected multiple times. "
                "Consider interview timing and duration."
            )
        
        if not recommendations:
            recommendations.append(
                "✅ <b>Excellent Performance:</b> No significant issues detected. "
                "Interview was conducted with excellent integrity and professionalism."
            )
        
        rec_style = ParagraphStyle(
            'RecStyle',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=10,
            leftIndent=20,
            rightIndent=20
        )
        
        for rec in recommendations:
            elements.append(Paragraph(rec, rec_style))
            elements.append(Spacer(1, 8))
        
        elements.append(Spacer(1, 20))
        
        # Footer with disclaimer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_CENTER,
            spaceAfter=5
        )
        
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            "<i>This report was automatically generated by the Proctoring System.</i>",
            footer_style
        ))
        elements.append(Paragraph(
            "<i>For questions or concerns, please contact the system administrator.</i>",
            footer_style
        ))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        logger.info(f"PDF report generated successfully for {report.candidate_name}")
        return buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error generating PDF report: {e}", exc_info=True)
        raise


def generate_csv(report):
    """Generate CSV report with enhanced data"""
    try:
        output = BytesIO()
        
        # Use TextIOWrapper for proper string handling
        import io
        text_output = io.TextIOWrapper(output, encoding='utf-8', newline='')
        writer = csv.writer(text_output)
        
        # Write header with metadata
        writer.writerow(['Interview Proctoring Report - CSV Export'])
        writer.writerow(['Generated:', timezone.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])  # Empty row
        
        # Write report data
        writer.writerow(['=== BASIC INFORMATION ==='])
        writer.writerow(['Field', 'Value'])
        writer.writerow(['Candidate Name', report.candidate_name])
        writer.writerow(['Interview Title', report.interview.title])
        writer.writerow(['Interview Date', report.interview.start_time.strftime('%Y-%m-%d %H:%M') if report.interview.start_time else 'N/A'])
        writer.writerow(['Duration', str(report.total_duration) if report.total_duration else 'N/A'])
        writer.writerow(['Report Generated', report.generated_at.strftime('%Y-%m-%d %H:%M')])
        writer.writerow([])  # Empty row
        
        # Integrity Score
        writer.writerow(['=== INTEGRITY ASSESSMENT ==='])
        writer.writerow(['Integrity Score', report.integrity_score])
        
        if report.integrity_score >= 90:
            grade = "A - Excellent"
        elif report.integrity_score >= 80:
            grade = "B - Good"
        elif report.integrity_score >= 70:
            grade = "C - Fair"
        elif report.integrity_score >= 60:
            grade = "D - Poor"
        else:
            grade = "F - Critical"
        
        writer.writerow(['Grade', grade])
        writer.writerow([])  # Empty row
        
        # Detection Events
        writer.writerow(['=== DETECTION EVENTS ==='])
        writer.writerow(['Event Type', 'Count', 'Severity'])
        writer.writerow(['Focus Lost Events', report.focus_lost_events, 'Medium'])
        writer.writerow(['No Face Detected', report.no_face_events, 'Medium'])
        writer.writerow(['Multiple Faces', report.multiple_faces_events, 'High'])
        writer.writerow(['Phone Detected', report.phone_detected_events, 'High'])
        writer.writerow(['Notes Detected', report.notes_detected_events, 'High'])
        writer.writerow(['Device Detected', report.device_detected_events, 'High'])
        writer.writerow(['Drowsiness Detected', report.drowsiness_events, 'Medium'])
        writer.writerow(['Audio Anomalies', report.audio_anomaly_events, 'Low'])
        writer.writerow([])  # Empty row
        
        # Severity Summary
        high_severity = (report.multiple_faces_events + report.phone_detected_events + 
                        report.notes_detected_events + report.device_detected_events)
        medium_severity = (report.focus_lost_events + report.no_face_events + 
                          report.drowsiness_events)
        low_severity = report.audio_anomaly_events
        
        writer.writerow(['=== SEVERITY SUMMARY ==='])
        writer.writerow(['Severity Level', 'Count'])
        writer.writerow(['High Severity Events', high_severity])
        writer.writerow(['Medium Severity Events', medium_severity])
        writer.writerow(['Low Severity Events', low_severity])
        writer.writerow(['Total Events', high_severity + medium_severity + low_severity])
        writer.writerow([])  # Empty row
        
        # Quality Metrics
        writer.writerow(['=== QUALITY METRICS ==='])
        writer.writerow(['Metric', 'Score'])
        writer.writerow(['Face Detection Accuracy', f"{report.face_detection_accuracy:.4f}"])
        writer.writerow(['Audio Quality Score', f"{report.audio_quality_score:.4f}"])
        writer.writerow(['Total Suspicious Events', report.suspicious_events])
        writer.writerow(['Total Focus Loss Count', report.focus_loss_count])
        writer.writerow([])  # Empty row
        
        # Interview Details
        writer.writerow(['=== INTERVIEW DETAILS ==='])
        writer.writerow(['Interviewer', report.interview.interviewer.get_full_name() or report.interview.interviewer.username])
        writer.writerow(['Status', report.interview.get_status_display()])
        writer.writerow(['Scheduled Time', report.interview.scheduled_time.strftime('%Y-%m-%d %H:%M')])
        
        if report.interview.start_time:
            writer.writerow(['Start Time', report.interview.start_time.strftime('%Y-%m-%d %H:%M')])
        if report.interview.end_time:
            writer.writerow(['End Time', report.interview.end_time.strftime('%Y-%m-%d %H:%M')])
        
        # Flush the text wrapper
        text_output.flush()
        text_output.detach()
        
        output.seek(0)
        
        logger.info(f"CSV report generated successfully for {report.candidate_name}")
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Error generating CSV report: {e}", exc_info=True)
        raise
