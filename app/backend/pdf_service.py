import io
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw, ImageFont

def generate_study_pdf(study_data: Dict[str, Any], user_email: str = "scholar@fivemetalmasonry.com") -> io.BytesIO:
    """
    Generates a museum-grade archival PDF document for an iconographical study.
    Attempts using ReportLab for vector typography and crisp layout;
    falls back cleanly to PIL-based high-res PDF generation if ReportLab is unavailable.
    """
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak, KeepTogether
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfgen import canvas
        
        buffer = io.BytesIO()
        
        class NumberedCanvas(canvas.Canvas):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._saved_page_states = []

            def showPage(self):
                self._saved_page_states.append(dict(self.__dict__))
                self._startPage()

            def save(self):
                num_pages = len(self._saved_page_states)
                for state in self._saved_page_states:
                    self.__dict__.update(state)
                    self.draw_page_decorations(num_pages)
                    super().showPage()
                super().save()

            def draw_page_decorations(self, page_count):
                self.saveState()
                self.setFont("Helvetica", 8)
                self.setFillColor(colors.HexColor("#7A6E5D"))
                
                # Header
                self.drawString(54, 800, "FIVE METAL MASONRY — SACRED ICONOGRAPHY ARCHIVE")
                self.drawRightString(540, 800, study_data.get("study_number", "Study 001"))
                self.setStrokeColor(colors.HexColor("#D4AF37"))
                self.setLineWidth(0.75)
                self.line(54, 792, 540, 792)
                
                # Footer & Watermark
                self.line(54, 45, 540, 45)
                self.drawString(54, 32, f"Licensed to: {user_email} · Panchaloha Research Edition")
                self.drawRightString(540, 32, f"Page {self._pageNumber} of {page_count}")
                
                # Subtle diagonal background watermark
                self.setFont("Helvetica-Bold", 32)
                self.setFillColor(colors.HexColor("#F5EBE6"))
                self.rotate(35)
                self.drawString(180, 200, "FIVE METAL MASONRY")
                self.restoreState()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54
        )
        
        styles = getSampleStyleSheet()
        
        # Custom bronze typography styles
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#1A1815"),
            spaceAfter=6
        )
        subtitle_style = ParagraphStyle(
            'DocSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#B58B4B"),
            spaceAfter=14
        )
        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#8C6D37"),
            spaceBefore=12,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            'DocBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#2C2824"),
            spaceAfter=8
        )
        ocr_corpus_style = ParagraphStyle(
            'OcrCorpus',
            parent=styles['Normal'],
            fontName='Courier',
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#3D372F")
        )
        badge_style = ParagraphStyle(
            'BadgeStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#FFFFFF")
        )

        elements = []
        
        # Title & Series
        series_name = study_data.get("series_name", "Sacred Iconography Series")
        study_num = study_data.get("study_number", "Study")
        title = study_data.get("title", "Canonical Iconography Study")
        subtitle = study_data.get("subtitle", "")
        summary = study_data.get("summary") or study_data.get("summary_markdown", "")
        
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"<b>{series_name.upper()} · {study_num}</b>", subtitle_style))
        elements.append(Paragraph(title, title_style))
        if subtitle:
            elements.append(Paragraph(subtitle, subtitle_style))
            
        elements.append(Spacer(1, 8))
        
        # Metadata Table
        meta_data = [
            [
                Paragraph("<b>Access Tier</b>", body_style),
                Paragraph(str(study_data.get("access_level", "member_only")).title(), body_style),
                Paragraph("<b>Total Plates</b>", body_style),
                Paragraph(str(len(study_data.get("slides", []))), body_style)
            ],
            [
                Paragraph("<b>Curator Verified</b>", body_style),
                Paragraph("Yes (Shilpa Shastra Canon)", body_style),
                Paragraph("<b>License Type</b>", body_style),
                Paragraph("Research & Scholarly Use", body_style)
            ]
        ]
        t = Table(meta_data, colWidths=[110, 140, 110, 140])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FAF7F2")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#E5D7C3")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5D7C3")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 14))
        
        # Abstract / Summary
        if summary:
            elements.append(Paragraph("<b>ICONOMETRICAL ABSTRACT & SUMMARY</b>", section_heading))
            # Clean markdown formatting for reportlab
            clean_sum = summary.replace("#", "").replace("**", "<b>").replace("__", "<b>")
            elements.append(Paragraph(clean_sum, body_style))
            elements.append(Spacer(1, 10))
            
        # Taxonomy Highlights
        taxonomy = study_data.get("taxonomy", [])
        if taxonomy:
            elements.append(Paragraph("<b>CONTROLLED ICONOGRAPHIC TAXONOMY TERMS</b>", section_heading))
            tax_rows = [[Paragraph("<b>Canonical Term</b>", body_style), Paragraph("<b>IAST Diacritic</b>", body_style), Paragraph("<b>Category</b>", body_style)]]
            for term_item in taxonomy[:8]:
                tax_rows.append([
                    Paragraph(term_item.get("term", ""), body_style),
                    Paragraph(term_item.get("iast", ""), body_style),
                    Paragraph(term_item.get("category", ""), body_style)
                ])
            tax_table = Table(tax_rows, colWidths=[160, 170, 170])
            tax_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F0E6D2")),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#D4AF37")),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5D7C3")),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(tax_table)
            elements.append(Spacer(1, 14))

        # Slides / Plates
        slides = study_data.get("slides", [])
        if slides:
            elements.append(PageBreak())
            for idx, sl in enumerate(slides):
                sl_title = sl.get("slide_title") or f"Archival Plate {sl.get('slide_number', idx+1)}"
                sl_num = sl.get("slide_number", idx + 1)
                img_path_rel = sl.get("image_url", "")
                
                elements.append(Paragraph(f"<b>PLATE {sl_num}: {sl_title.upper()}</b>", section_heading))
                if sl.get("caption"):
                    elements.append(Paragraph(f"<i>{sl.get('caption')}</i>", subtitle_style))
                
                # Check local image file
                clean_img_path = img_path_rel.lstrip("/")
                if clean_img_path.startswith("storage/"):
                    clean_img_path = clean_img_path.replace("storage/", "", 1)
                
                img_full_path = Path(__file__).resolve().parent / "storage" / clean_img_path
                if not img_full_path.exists():
                    img_full_path = Path(__file__).resolve().parent / "storage" / "images" / clean_img_path
                
                if img_full_path.exists():
                    try:
                        # Add image sized proportionally
                        elements.append(RLImage(str(img_full_path), width=480, height=280, kind='proportional'))
                        elements.append(Spacer(1, 8))
                    except Exception as img_err:
                        elements.append(Paragraph(f"[Plate Image: {sl_title}]", body_style))
                
                # OCR Corpus block
                raw_ocr = sl.get("cleaned_text") or sl.get("raw_ocr") or ""
                if raw_ocr:
                    elements.append(Paragraph("<b>Extracted Inscription & Epigraphical Corpus:</b>", body_style))
                    ocr_box = Table([[Paragraph(raw_ocr.replace("\n", "<br/>"), ocr_corpus_style)]], colWidths=[500])
                    ocr_box.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8F6F0")),
                        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor("#D4AF37")),
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ]))
                    elements.append(ocr_box)
                
                elements.append(Spacer(1, 14))
                if idx < len(slides) - 1:
                    elements.append(PageBreak())

        doc.build(elements, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer

    except Exception as e:
        print(f"ReportLab PDF generation error, falling back to PIL: {e}")
        return generate_fallback_pillow_pdf(study_data, user_email)


def generate_fallback_pillow_pdf(study_data: Dict[str, Any], user_email: str) -> io.BytesIO:
    """
    Fallback pure-Pillow PDF generator for high reliability.
    """
    pages = []
    width, height = 1240, 1754  # A4 150 DPI
    
    # Page 1: Overview
    cover = Image.new("RGB", (width, height), color=(250, 247, 242))
    draw = ImageDraw.Draw(cover)
    
    # Decorative border
    draw.rectangle([(40, 40), (width - 40, height - 40)], outline=(212, 175, 55), width=3)
    draw.text((60, 60), "FIVE METAL MASONRY — SACRED ICONOGRAPHY ARCHIVE", fill=(140, 109, 55))
    
    title = study_data.get("title", "Canonical Iconography Study")
    series_name = study_data.get("series_name", "Sacred Iconography Series")
    study_num = study_data.get("study_number", "Study 001")
    
    draw.text((60, 120), f"{series_name.upper()} · {study_num}", fill=(181, 139, 75))
    draw.text((60, 160), title, fill=(26, 24, 21))
    
    summary = study_data.get("summary") or study_data.get("summary_markdown", "Archival research iconograph.")
    lines = [summary[i:i+90] for i in range(0, len(summary), 90)]
    y = 220
    for l in lines[:10]:
        draw.text((60, y), l, fill=(60, 55, 48))
        y += 24
        
    draw.text((60, height - 80), f"Licensed to: {user_email} · Research Edition", fill=(140, 109, 55))
    pages.append(cover)
    
    # Slide pages
    for sl in study_data.get("slides", []):
        p = Image.new("RGB", (width, height), color=(255, 255, 255))
        p_draw = ImageDraw.Draw(p)
        p_draw.rectangle([(40, 40), (width - 40, height - 40)], outline=(212, 175, 55), width=2)
        
        sl_title = sl.get("slide_title", "Archival Plate")
        p_draw.text((60, 60), f"PLATE {sl.get('slide_number', 1)}: {sl_title}", fill=(26, 24, 21))
        
        ocr_text = sl.get("cleaned_text") or sl.get("raw_ocr") or ""
        if ocr_text:
            p_draw.text((60, height - 200), "Extracted Inscription & Epigraphy Corpus:", fill=(140, 109, 55))
            ocr_lines = [ocr_text[i:i+80] for i in range(0, len(ocr_text), 80)]
            oy = height - 170
            for ol in ocr_lines[:5]:
                p_draw.text((60, oy), ol, fill=(70, 65, 58))
                oy += 20
                
        p_draw.text((60, height - 80), f"Licensed to: {user_email} · Five Metal Masonry Archive", fill=(140, 109, 55))
        pages.append(p)
        
    buf = io.BytesIO()
    if pages:
        pages[0].save(buf, format="PDF", save_all=True, append_images=pages[1:], resolution=150.0)
    buf.seek(0)
    return buf
