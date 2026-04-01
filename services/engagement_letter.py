"""
GigHala Fractional Engagement Letter Generator
================================================
Generates a professional PDF engagement letter for a fractional / retained
role using ReportLab (already a project dependency).

Usage:
    from services.engagement_letter import generate_engagement_letter
    buffer = generate_engagement_letter(escrow)
    # buffer is a BytesIO — call buffer.getvalue() for raw bytes.

Circular-import note: Gig and User are imported lazily inside the function.
"""

import logging
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

logger = logging.getLogger(__name__)

# Brand colours
BRAND_GREEN = colors.HexColor('#00C853')   # GigHala primary green
BRAND_DARK  = colors.HexColor('#1a1a2e')   # Near-black for headings
LIGHT_GREEN = colors.HexColor('#e8f5e9')   # Pale green for table headers
LIGHT_GREY  = colors.HexColor('#f5f5f5')   # Alternating row tint
MID_GREY    = colors.HexColor('#9e9e9e')   # Footer / secondary text

MALAY_MONTHS = {
    1: 'Januari', 2: 'Februari', 3: 'Mac', 4: 'April',
    5: 'Mei', 6: 'Jun', 7: 'Julai', 8: 'Ogos',
    9: 'September', 10: 'Oktober', 11: 'November', 12: 'Disember',
}


def _ms_date(dt):
    """Format a datetime as "1 Januari 2025" (Bahasa Malaysia)."""
    if not dt:
        return '—'
    return f'{dt.day} {MALAY_MONTHS[dt.month]} {dt.year}'


def _fmt_myr(value):
    """Format a numeric value as "MYR 1,234.00"."""
    try:
        return f'MYR {float(value):,.2f}'
    except (TypeError, ValueError):
        return 'MYR —'


def generate_engagement_letter(escrow):
    """Generate a PDF engagement letter for a fractional retainer engagement.

    Fetches Gig, client User, and freelancer User from the escrow record.

    Args:
        escrow: Escrow model instance (must have gig_id, client_id,
                freelancer_id, retainer_start_date, amount, platform_fee,
                net_amount).

    Returns:
        BytesIO buffer containing the PDF.

    Raises:
        Exception if critical data (gig, client, freelancer) cannot be loaded.
    """
    from app import Gig, User

    gig        = Gig.query.get(escrow.gig_id)
    client     = User.query.get(escrow.client_id)
    freelancer = User.query.get(escrow.freelancer_id)

    if not gig or not client or not freelancer:
        raise ValueError(
            f'Missing data: gig={gig}, client={client}, freelancer={freelancer}'
        )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2.2 * cm,
        leftMargin=2.2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    base = getSampleStyleSheet()
    elements = []

    # ------------------------------------------------------------------
    # Custom paragraph styles
    # ------------------------------------------------------------------
    header_title = ParagraphStyle(
        'HeaderTitle',
        parent=base['Normal'],
        fontSize=22,
        fontName='Helvetica-Bold',
        textColor=BRAND_GREEN,
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    header_sub = ParagraphStyle(
        'HeaderSub',
        parent=base['Normal'],
        fontSize=10,
        textColor=MID_GREY,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=base['Normal'],
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=BRAND_DARK,
        spaceBefore=14,
        spaceAfter=4,
    )
    body = ParagraphStyle(
        'Body',
        parent=base['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=4,
    )
    clause_body = ParagraphStyle(
        'ClauseBody',
        parent=base['Normal'],
        fontSize=9,
        leading=13,
        leftIndent=10,
        spaceAfter=6,
    )
    footer_style = ParagraphStyle(
        'Footer',
        parent=base['Normal'],
        fontSize=8,
        textColor=MID_GREY,
        alignment=TA_CENTER,
    )

    def hr():
        return HRFlowable(
            width='100%', thickness=0.5,
            color=BRAND_GREEN, spaceAfter=6, spaceBefore=4
        )

    def section(title):
        elements.append(Spacer(1, 0.2 * cm))
        elements.append(hr())
        elements.append(Paragraph(title.upper(), section_heading))

    # ------------------------------------------------------------------
    # 1. Header
    # ------------------------------------------------------------------
    elements.append(Paragraph('GigHala', header_title))
    elements.append(Paragraph(
        'gighala.my &nbsp;|&nbsp; Platform Bakat Halal Disahkan', header_sub
    ))
    elements.append(Paragraph(
        '<b>SURAT PENGLIBATAN FRACTIONAL</b>',
        ParagraphStyle(
            'DocTitle', parent=base['Normal'],
            fontSize=14, fontName='Helvetica-Bold',
            textColor=BRAND_DARK, alignment=TA_CENTER,
            spaceBefore=6, spaceAfter=2,
        )
    ))
    elements.append(Paragraph(
        f'Tarikh: {_ms_date(datetime.utcnow())}',
        ParagraphStyle(
            'DocDate', parent=base['Normal'],
            fontSize=10, textColor=MID_GREY, alignment=TA_CENTER, spaceAfter=6,
        )
    ))

    # ------------------------------------------------------------------
    # 2. Pihak-Pihak (Parties)
    # ------------------------------------------------------------------
    section('Pihak-Pihak Yang Terlibat')

    client_name     = client.full_name or client.username
    freelancer_name = freelancer.full_name or freelancer.username

    parties_data = [
        ['', 'Klien', 'Pakar / Eksekutif Fractional'],
        ['Nama',  client_name,     freelancer_name],
        ['E-mel', client.email,    freelancer.email],
    ]
    parties_table = Table(
        parties_data,
        colWidths=[3 * cm, 8 * cm, 6.5 * cm],
    )
    parties_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GREEN),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, 0), 9),
        ('TEXTCOLOR',  (0, 0), (-1, 0), BRAND_DARK),
        ('FONTNAME',   (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',   (0, 1), (-1, -1), 9),
        ('ALIGN',      (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',       (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ('TOPPADDING',  (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(parties_table)

    # ------------------------------------------------------------------
    # 3. Perincian Penglibatan (Engagement Details)
    # ------------------------------------------------------------------
    section('Perincian Penglibatan')

    days_str = (
        f'{float(gig.commitment_days_per_week):.1f} hari per minggu'
        if gig.commitment_days_per_week else '—'
    )
    duration_str = (
        f'{gig.engagement_duration_months} bulan'
        if gig.engagement_duration_months else '—'
    )

    details_data = [
        ['Peranan',            gig.title],
        ['Kategori',           gig.category or '—'],
        ['Industri',           gig.industry_focus or '—'],
        ['Lokasi Kerja',       (gig.remote_onsite or '—').capitalize()],
        ['Komitmen',           days_str],
        ['Tempoh Penglibatan', duration_str],
        ['Tarikh Mula',        _ms_date(escrow.retainer_start_date)],
        ['Bayaran Bulanan',    _fmt_myr(gig.monthly_retainer_amount or escrow.amount)],
        ['Yuran Platform (8%)', _fmt_myr(escrow.platform_fee)],
        ['Amaun Bersih Pakar', _fmt_myr(escrow.net_amount)],
    ]
    details_table = Table(details_data, colWidths=[5.5 * cm, 12 * cm])
    details_table.setStyle(TableStyle([
        ('FONTNAME',   (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, -1), 9),
        ('ALIGN',      (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',       (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, LIGHT_GREY]),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        # Highlight net amount row
        ('BACKGROUND', (0, 9), (-1, 9), LIGHT_GREEN),
        ('FONTNAME',   (0, 9), (-1, 9), 'Helvetica-Bold'),
    ]))
    elements.append(details_table)

    # ------------------------------------------------------------------
    # 4. Skop Kerja (Scope of Work)
    # ------------------------------------------------------------------
    section('Skop Kerja')
    # Escape any XML-unfriendly chars in the description
    scope_text = (gig.description or '—').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    elements.append(Paragraph(scope_text, body))

    # ------------------------------------------------------------------
    # 5. Klausa Standard (Standard Clauses)
    # ------------------------------------------------------------------
    section('Terma dan Syarat')

    clauses = [
        (
            'KERAHSIAAN',
            'Kedua-dua pihak bersetuju untuk merahsiakan semua maklumat sulit '
            'yang diperoleh semasa penglibatan ini selama <b>24 bulan</b> selepas '
            'tamat penglibatan, melainkan diwajibkan oleh undang-undang.'
        ),
        (
            'PENAMATAN',
            'Mana-mana pihak boleh menamatkan penglibatan ini dengan memberikan '
            '<b>notis bertulis 30 hari</b> kepada pihak yang satu lagi. Semua '
            'pembayaran yang tertunggak sehingga tarikh notis mesti diselesaikan '
            'sepenuhnya.'
        ),
        (
            'PEMILIKAN HARTA INTELEK',
            'Semua hasil kerja, laporan, kod, reka bentuk, dan bahan lain yang '
            'dihasilkan oleh Pakar dalam tempoh penglibatan ini adalah <b>milik '
            'penuh Klien</b> setelah pembayaran penuh diterima.'
        ),
        (
            'PEMATUHAN HALAL',
            'Kedua-dua pihak mengesahkan bahawa penglibatan ini mematuhi etika '
            'perniagaan Islam dan <b>bebas daripada riba, gharar</b>, serta '
            'sebarang aktiviti yang dilarang di bawah Syariah. GigHala berperanan '
            'sebagai platform halal yang disahkan.'
        ),
        (
            'UNDANG-UNDANG YANG TERPAKAI',
            'Perjanjian ini tertakluk kepada <b>Undang-Undang Malaysia</b>. '
            'Sebarang pertikaian hendaklah diselesaikan di bawah bidang kuasa '
            'eksklusif mahkamah <b>Kuala Lumpur, Malaysia</b>.'
        ),
    ]

    for title, text in clauses:
        elements.append(Paragraph(
            f'<b>{title}</b>',
            ParagraphStyle(
                'ClauseTitle', parent=base['Normal'],
                fontSize=9, fontName='Helvetica-Bold',
                textColor=BRAND_DARK, spaceBefore=8, spaceAfter=2,
            )
        ))
        elements.append(Paragraph(text, clause_body))

    # ------------------------------------------------------------------
    # 6. Blok Tandatangan (Signature Block)
    # ------------------------------------------------------------------
    section('Tandatangan')

    sig_data = [
        ['Pihak',       'Nama',           'Tandatangan',             'Tarikh'],
        ['Klien',       client_name,      '_' * 28,                  '____________'],
        ['Pakar',       freelancer_name,  '_' * 28,                  '____________'],
        ['GigHala\n(Saksi)', 'GigHala',  '_' * 28,                  '____________'],
    ]
    sig_table = Table(
        sig_data,
        colWidths=[3 * cm, 5 * cm, 6.5 * cm, 3 * cm],
    )
    sig_table.setStyle(TableStyle([
        ('BACKGROUND',  (0, 0), (-1, 0), BRAND_GREEN),
        ('TEXTCOLOR',   (0, 0), (-1, 0), colors.white),
        ('FONTNAME',    (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0, 0), (-1, -1), 9),
        ('ALIGN',       (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',        (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(sig_table)

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(hr())
    elements.append(Paragraph(
        f'Dokumen ini dijana secara elektronik oleh GigHala &mdash; '
        f'gighala.my &nbsp;|&nbsp; Platform Bakat Halal #1 Malaysia<br/>'
        f'Dijana pada: {datetime.utcnow().strftime("%d %B %Y pukul %H:%M")} UTC',
        footer_style,
    ))

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    doc.build(elements)
    buffer.seek(0)
    return buffer
