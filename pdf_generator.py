"""
PDF Executive Report Generator for IDT Analyzer
Generates a visual, executive-level PDF report following Thomson Reuters brand guidelines
"""
import io
import os
import re
from datetime import datetime
from xml.sax.saxutils import escape as _xml_escape
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Thomson Reuters Brand: Typography ──────────────────────────────────────
_FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

pdfmetrics.registerFont(TTFont("Clario", os.path.join(_FONTS_DIR, "Clario-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Clario-Medium", os.path.join(_FONTS_DIR, "Clario-Medium.ttf")))
pdfmetrics.registerFont(TTFont("Clario-Bold", os.path.join(_FONTS_DIR, "Clario-Bold.ttf")))
pdfmetrics.registerFont(TTFont("Clario-Light", os.path.join(_FONTS_DIR, "Clario-Light.ttf")))
pdfmetrics.registerFontFamily(
    "Clario", normal="Clario", bold="Clario-Bold",
    italic="Clario", boldItalic="Clario-Bold"
)

# ── Thomson Reuters Brand: Color Palette ───────────────────────────────────
TR_GREEN = colors.HexColor('#123121')       # Racing Green - alternate primary / dark bg
TR_ORANGE = colors.HexColor('#D64000')      # Primary brand color
TR_BLACK = colors.HexColor('#000000')
TR_WHITE = colors.HexColor('#FFFFFF')

TR_DARK_GOLD = colors.HexColor('#E9B045')
TR_DARK_AMBER = colors.HexColor('#D4792A')
TR_DARK_SKY = colors.HexColor('#0874E3')
TR_DARK_TEAL = colors.HexColor('#4DB299')
TR_DARK_LIME = colors.HexColor('#8FCB64')

TR_LIGHT_GOLD = colors.HexColor('#FCF2DA')
TR_LIGHT_AMBER = colors.HexColor('#F8EADD')
TR_LIGHT_SKY = colors.HexColor('#E3F1FD')
TR_LIGHT_TEAL = colors.HexColor('#E3F3EE')
TR_LIGHT_LIME = colors.HexColor('#E1F4CD')

TR_BORDER_GREY = colors.HexColor('#DDDDDD')


def score_color(score):
    """Return TR-branded accent color based on score band"""
    if score is None:
        return colors.grey
    if score >= 80:
        return TR_DARK_TEAL
    if score >= 50:
        return TR_DARK_GOLD
    return TR_ORANGE


def score_bg_color(score):
    """Return TR-branded light background color matching score_color"""
    if score is None:
        return colors.HexColor('#f0f0f0')
    if score >= 80:
        return TR_LIGHT_TEAL
    if score >= 50:
        return TR_LIGHT_GOLD
    return TR_LIGHT_AMBER


def get_status_text(score):
    """Return status text based on score"""
    if score is None:
        return "N/A"
    if score >= 90:
        return "Excelente"
    if score >= 80:
        return "Bom"
    if score >= 50:
        return "Atenção"
    return "Crítico"


def cfop_standard_status(cfop_value, non_standard_cfops):
    """Classifica um CFOP declarado quanto ao atendimento via standard IDT"""
    if not cfop_value:
        return "—"
    cfop_clean = re.sub(r'[^\d]', '', str(cfop_value))
    if not cfop_clean:
        return "—"
    if cfop_clean in non_standard_cfops:
        return "Customização"
    return "Standard"


def split_cfops_by_direction(cfop_list):
    """
    Separa uma lista de CFOPs em Entrada (Compras) e Saída (Vendas)
    conforme a convenção oficial do primeiro dígito do CFOP:
    1-3 = Entrada · 5-7 = Saída
    """
    entrada, saida = [], []
    for cfop in cfop_list:
        digits = re.sub(r'[^\d]', '', str(cfop))
        if not digits:
            continue
        if digits[0] in '123':
            entrada.append(cfop)
        elif digits[0] in '567':
            saida.append(cfop)
    return sorted(entrada), sorted(saida)


_CELL_TEXT_STYLE = ParagraphStyle(
    'CellText', fontName='Clario', fontSize=8, leading=10, alignment=TA_LEFT, wordWrap='CJK'
)


def cell_text(value, style=None):
    """
    Envolve texto de célula em um Paragraph para permitir quebra de linha
    automática dentro da largura da coluna, em vez de vazar da caixa.
    Não trunca o conteúdo — o texto completo é sempre preservado.
    """
    text = "" if value is None else str(value)
    return Paragraph(_xml_escape(text), style or _CELL_TEXT_STYLE)


def create_paginated_table(data_rows, columns, col_widths, title, story, heading_style, items_per_page=25):
    """
    Cria tabela paginada para listas longas.
    """
    if not data_rows:
        return

    if title:
        story.append(Paragraph(title, heading_style))
        story.append(Spacer(1, 0.3 * cm))

    total_items = len(data_rows)
    num_pages = (total_items + items_per_page - 1) // items_per_page

    for page_num in range(num_pages):
        start_idx = page_num * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)

        if num_pages > 1:
            italic_style = ParagraphStyle('Italic', fontName='Clario', fontSize=9,
                                           textColor=colors.grey, alignment=TA_CENTER)
            story.append(Paragraph(
                f"Página {page_num + 1} de {num_pages} (itens {start_idx + 1}-{end_idx} de {total_items})",
                italic_style
            ))
            story.append(Spacer(1, 0.2 * cm))

        page_data = [columns] + [
            [cell_text(cell) for cell in row]
            for row in data_rows[start_idx:end_idx]
        ]

        table = Table(page_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), TR_GREEN),
            ('TEXTCOLOR', (0, 0), (-1, 0), TR_WHITE),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Clario-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Clario'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, TR_BORDER_GREY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [TR_WHITE, TR_LIGHT_GOLD]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))

        story.append(table)

        if page_num < num_pages - 1:
            story.append(PageBreak())


def _build_styles():
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Title'], fontSize=26,
        textColor=TR_WHITE, spaceAfter=6, alignment=TA_CENTER, fontName='Clario-Bold'
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle', parent=styles['Heading2'], fontSize=13,
        textColor=TR_DARK_GOLD, alignment=TA_CENTER, fontName='Clario-Medium'
    )
    heading_style = ParagraphStyle(
        'CustomHeading', parent=styles['Heading1'], fontSize=16,
        textColor=TR_GREEN, spaceAfter=12, spaceBefore=20, fontName='Clario-Bold'
    )
    subheading_style = ParagraphStyle(
        'CustomSubHeading', parent=styles['Heading2'], fontSize=12,
        textColor=TR_ORANGE, spaceAfter=10, fontName='Clario-Bold'
    )
    subsub_style = ParagraphStyle(
        'SubSub', fontName='Clario-Bold', fontSize=11, textColor=TR_GREEN
    )
    body_style = ParagraphStyle(
        'CustomBody', parent=styles['Normal'], fontSize=10, leading=14,
        alignment=TA_JUSTIFY, fontName='Clario'
    )
    caption_style = ParagraphStyle(
        'Caption', fontName='Clario-Light', fontSize=8, textColor=colors.grey
    )
    return {
        'title': title_style, 'subtitle': subtitle_style, 'heading': heading_style,
        'subheading': subheading_style, 'subsub': subsub_style, 'body': body_style,
        'caption': caption_style,
    }


def _card_number_style(color):
    return ParagraphStyle('CardNumber', fontName='Clario-Bold', fontSize=26, leading=32,
                           textColor=color, alignment=TA_CENTER)


def _card_label_style():
    return ParagraphStyle('CardLabel', fontName='Clario', fontSize=8, leading=11,
                           textColor=TR_BLACK, alignment=TA_CENTER)


def generate_pdf(result: dict, filename: str = "relatorio_idt.pdf",
                  cliente_nome: str = None, cliente_segmento: str = None) -> bytes:
    """
    Generate executive PDF report with Thomson Reuters brand guidelines
    Returns: PDF bytes
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm
    )

    s = _build_styles()
    story = []

    general = result.get("general", {})
    nc = result['ncm_compras']
    nv = result['ncm_vendas']
    m = result['municipios']
    cfops = result.get('cfops', {})
    non_standard_cfops = set(cfops.get('non_standard', []))

    nome_cliente = cliente_nome if cliente_nome else general.get("segmento", "N/A")
    segmento_exibicao = cliente_segmento if cliente_segmento else general.get("segmento", "N/A")

    # ═══════════════════════════════════════════════════════════════════════
    # 1. CAPA
    # ═══════════════════════════════════════════════════════════════════════
    cover_band = Table([[
        Paragraph("IDT · Relatório de Aderência", s['title']),
    ]], colWidths=[17 * cm], rowHeights=[2.2 * cm])
    cover_band.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), TR_GREEN),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, -1), 3, TR_ORANGE),
    ]))
    story.append(cover_band)
    story.append(Paragraph("Análise de Pré-Diagnóstico Fiscal · Onesource Determination", s['subtitle']))
    story.append(Spacer(1, 1 * cm))

    client_info = [
        ["Cliente", cell_text(nome_cliente)],
        ["Segmento", cell_text(segmento_exibicao)],
        ["Data da Análise", datetime.now().strftime("%d/%m/%Y")],
    ]
    client_table = Table(client_info, colWidths=[4.5 * cm, 12.5 * cm])
    client_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), TR_GREEN),
        ('TEXTCOLOR', (0, 0), (0, -1), TR_WHITE),
        ('TEXTCOLOR', (1, 0), (1, -1), TR_BLACK),
        ('FONTNAME', (0, 0), (0, -1), 'Clario-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Clario'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 0.5, TR_BORDER_GREY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(client_table)
    story.append(Spacer(1, 1 * cm))

    # ═══════════════════════════════════════════════════════════════════════
    # 2. RESUMO EXECUTIVO (ROBUSTO)
    # ═══════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Resumo Executivo", s['heading']))

    overall = result.get('overall_score')
    overall_color = score_color(overall)
    overall_bg = score_bg_color(overall)

    score_card = Table([[
        Paragraph(f"{overall:.1f}%" if overall is not None else "N/A", _card_number_style(overall_color)),
        Paragraph(
            f"<b>Score Geral de Aderência</b><br/>Classificação: <b>{get_status_text(overall)}</b><br/>"
            f"Cálculo ponderado entre NCM Compras, NCM Vendas e Municípios ISS "
            f"(ver Metodologia de Cálculo, ao final deste relatório).",
            s['body']
        ),
    ]], colWidths=[4 * cm, 13 * cm])
    score_card.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), overall_bg),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('LINEBEFORE', (0, 0), (0, -1), 4, overall_color),
        ('TOPPADDING', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('LEFTPADDING', (1, 0), (1, -1), 16),
    ]))
    story.append(score_card)
    story.append(Spacer(1, 0.6 * cm))

    scores_data = [
        ["Dimensão", "Score (%)", "Status"],
        ["NCM Compras", f"{nc.get('score', 0):.1f}%" if nc.get('score') is not None else "N/A",
         get_status_text(nc.get('score'))],
        ["NCM Vendas", f"{nv.get('score', 0):.1f}%" if nv.get('score') is not None else "N/A",
         get_status_text(nv.get('score'))],
        ["Municípios ISS", f"{m.get('score', 0):.1f}%" if m.get('score') is not None else "N/A",
         get_status_text(m.get('score'))],
    ]
    scores_table = Table(scores_data, colWidths=[6 * cm, 4 * cm, 5.5 * cm])
    scores_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TR_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), TR_WHITE),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Clario-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Clario'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, TR_BORDER_GREY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [TR_WHITE, TR_LIGHT_GOLD]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
    ]))
    story.append(scores_table)
    story.append(Spacer(1, 0.6 * cm))

    # Achados narrativos
    findings = []
    if nc.get('gaps') or nv.get('gaps'):
        total_gaps = len(nc.get('gaps', [])) + len(nv.get('gaps', []))
        findings.append(f"• <b>{total_gaps} pares NCM×UF</b> não possuem cobertura completa e requerem atenção.")
    if m.get('out_of_scope'):
        findings.append(f"• <b>{len(m['out_of_scope'])} municípios</b> não estão cobertos pela lista de aderência standard.")
    if m.get('invalid'):
        findings.append(f"• <b>{len(m['invalid'])} municípios</b> possuem UF não reconhecida/inválida e não puderam ser validados.")
    if cfops.get('alertas'):
        findings.append(f"• <b>{len(cfops['alertas'])} CFOPs</b> requerem customização (operações não-standard).")
    nc_score = nc.get('score')
    if nc_score is not None and nc_score >= 90:
        findings.append(f"• Excelente cobertura em <b>NCM Compras</b> ({nc_score:.1f}%).")
    nv_score = nv.get('score')
    if nv_score is not None and nv_score >= 90:
        findings.append(f"• Excelente cobertura em <b>NCM Vendas</b> ({nv_score:.1f}%).")
    if not findings:
        findings.append("• Nenhum ponto crítico identificado na análise consolidada.")

    story.append(Paragraph("Principais Achados", s['subsub']))
    story.append(Spacer(1, 0.2 * cm))
    for finding in findings:
        story.append(Paragraph(finding, s['body']))
        story.append(Spacer(1, 0.15 * cm))

    # ═══════════════════════════════════════════════════════════════════════
    # 3. PONTOS DE ATENÇÃO
    # ═══════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("Pontos de Atenção", s['heading']))
    story.append(Paragraph(
        "Indicadores que demonstram o que não é atendido pelo conteúdo standard do IDT e que deve ser customizado:",
        s['body']
    ))
    story.append(Spacer(1, 0.4 * cm))

    attention_cards = [
        (len(nc.get('gaps', [])) + len(nv.get('gaps', [])), "Pares NCM×UF\nnão atendidos", TR_ORANGE, TR_LIGHT_AMBER),
        (len(m.get('out_of_scope', [])), "Municípios\nfora do escopo", TR_DARK_GOLD, TR_LIGHT_GOLD),
        (len(m.get('invalid', [])), "Municípios\nnão entendidos (UF inválida)", TR_DARK_AMBER, TR_LIGHT_AMBER),
        (len(cfops.get('alertas', [])), "CFOPs não-standard\n(customização)", TR_DARK_AMBER, TR_LIGHT_AMBER),
        (sum(1 for csts in result.get('cst_coverage', {}).values()
             for v in csts.values() if not v), "CSTs\nnão atendidos", TR_DARK_SKY, TR_LIGHT_SKY),
    ]

    card_width = 17 * cm / len(attention_cards)

    card_row = []
    for count, label, fg, bg in attention_cards:
        cell = Table([
            [Paragraph(str(count), _card_number_style(fg))],
            [Paragraph(label.replace("\n", "<br/>"), _card_label_style())],
        ], colWidths=[card_width - 0.25 * cm])
        cell.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg),
            ('LINEABOVE', (0, 0), (-1, 0), 3, fg),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 1), (-1, 1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 14),
        ]))
        card_row.append(cell)

    cards_table = Table([card_row], colWidths=[card_width] * len(attention_cards))
    cards_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(cards_table)
    story.append(Spacer(1, 0.7 * cm))

    # Callout executivo: B2C
    b2c_text = Paragraph(
        "<b>Operações B2C não contempladas pelo conteúdo standard</b><br/>"
        "Operações de venda direta ao consumidor final (B2C) não são cobertas pelo conteúdo "
        "standard do IDT e demandam customização específica no escopo do projeto.",
        s['body']
    )
    b2c_callout = Table([[
        "",
        b2c_text,
    ]], colWidths=[0.3 * cm, 16.45 * cm])
    b2c_callout.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), TR_ORANGE),
        ('BACKGROUND', (1, 0), (1, -1), TR_LIGHT_GOLD),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, -1), 0),
        ('RIGHTPADDING', (0, 0), (0, -1), 0),
        ('LEFTPADDING', (1, 0), (1, -1), 14),
        ('TOPPADDING', (1, 0), (1, -1), 12),
        ('BOTTOMPADDING', (1, 0), (1, -1), 12),
        ('RIGHTPADDING', (1, 0), (1, -1), 12),
    ]))
    story.append(b2c_callout)

    # ═══════════════════════════════════════════════════════════════════════
    # 4. ITENS NÃO ATENDIDOS — DETALHES
    # ═══════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("Itens Não Atendidos — Detalhes", s['heading']))
    story.append(Paragraph(
        "Esta seção consolida os itens que requerem atenção por não estarem completamente cobertos pelo IDT standard:",
        s['body']
    ))
    story.append(Spacer(1, 0.5 * cm))

    if nc.get('gaps') or nv.get('gaps'):
        story.append(Paragraph("NCMs Não Atendidos", s['subheading']))
        story.append(Spacer(1, 0.2 * cm))
        total_ncm_gaps = len(nc.get('gaps', [])) + len(nv.get('gaps', []))
        story.append(Paragraph(f"<b>{total_ncm_gaps} pares NCM×UF</b> identificados sem cobertura completa:", s['body']))
        story.append(Spacer(1, 0.3 * cm))

        for label, gaps in [("Compras", nc.get('gaps', [])), ("Vendas", nv.get('gaps', []))]:
            if not gaps:
                continue
            story.append(Paragraph(f"<b>{label} ({len(gaps)} gaps):</b>", s['body']))
            rows = []
            for gap in gaps[:10]:
                desc = gap.get('Descricao', '')
                cov = gap.get('Cobertura', '')
                cov_str = f"{cov}%" if cov is not None and cov != '' else "N/A"
                cfop_status = cfop_standard_status(gap.get('CFOP'), non_standard_cfops)
                rows.append([
                    cell_text(gap.get('NCM', '')), cell_text(gap.get('UF', '')), cell_text(desc),
                    cell_text(gap.get('CFOP', '') or '—'), cell_text(cfop_status), cell_text(cov_str),
                ])
            table = Table(rows, colWidths=[2.2 * cm, 1.2 * cm, 6.3 * cm, 1.8 * cm, 2.6 * cm, 1.9 * cm])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Clario'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.3, TR_BORDER_GREY),
                ('ROWBACKGROUNDS', (0, 0), (-1, -1), [TR_WHITE, TR_LIGHT_AMBER]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(table)
            if len(gaps) > 10:
                story.append(Paragraph(
                    f"... e mais {len(gaps) - 10} itens (ver Detalhamento da Aderência, ao final)",
                    s['caption']
                ))
            story.append(Spacer(1, 0.3 * cm))

    def render_municipios_grid(city_list, limit=20):
        mun_list = sorted(city_list)[:limit]
        num_cols = 3
        rows_per_col = (len(mun_list) + num_cols - 1) // num_cols
        grid_data = []
        for i in range(rows_per_col):
            row = []
            for col in range(num_cols):
                idx = col * rows_per_col + i
                row.append(cell_text(mun_list[idx]) if idx < len(mun_list) else "")
            grid_data.append(row)
        if grid_data:
            mun_table = Table(grid_data, colWidths=[5.2 * cm] * num_cols)
            mun_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Clario'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.3, TR_BORDER_GREY),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(mun_table)
            if len(city_list) > limit:
                story.append(Paragraph(f"... e mais {len(city_list) - limit} municípios (ver Detalhamento da Aderência)", s['caption']))
            story.append(Spacer(1, 0.5 * cm))

    if m.get('out_of_scope'):
        story.append(Paragraph("Municípios Não Atendidos", s['subheading']))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(
            f"<b>{len(m['out_of_scope'])} municípios</b> não estão cobertos pela lista de aderência standard:",
            s['body']
        ))
        story.append(Spacer(1, 0.3 * cm))
        render_municipios_grid(m['out_of_scope'])

    if m.get('invalid'):
        story.append(Paragraph("Municípios Não Entendidos (UF Inválida)", s['subheading']))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(
            f"<b>{len(m['invalid'])} municípios</b> possuem UF não reconhecida ou não informada e não puderam "
            f"ser validados contra a lista de aderência:",
            s['body']
        ))
        story.append(Spacer(1, 0.3 * cm))
        render_municipios_grid(m['invalid'])

    cst_cov = result.get('cst_coverage', {})
    cst_nao_atendidos = {t: {c: ok for c, ok in csts.items() if not ok} for t, csts in cst_cov.items()}
    cst_nao_atendidos = {t: c for t, c in cst_nao_atendidos.items() if c}
    if cst_nao_atendidos:
        story.append(Paragraph("CSTs Não Atendidos", s['subheading']))
        story.append(Spacer(1, 0.2 * cm))
        for tributo, csts_dict in sorted(cst_nao_atendidos.items()):
            csts_list = ", ".join(sorted(csts_dict.keys()))
            story.append(Paragraph(f"<b>{tributo}:</b> {csts_list}", s['body']))
        story.append(Spacer(1, 0.5 * cm))

    if cfops.get('alertas'):
        story.append(Paragraph("CFOPs Não-Standard", s['subheading']))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(
            f"<b>{len(cfops['alertas'])} CFOPs</b> requerem customização (não são operações standard):",
            s['body']
        ))
        story.append(Spacer(1, 0.3 * cm))
        cfop_rows = []
        for alerta in cfops['alertas'][:15]:
            cfop_rows.append([
                cell_text(alerta.get('CFOP', '')),
                cell_text(alerta.get('Tipo', '')),
                cell_text(alerta.get('Mensagem', '')),
            ])
        cfop_table = Table(cfop_rows, colWidths=[2 * cm, 3 * cm, 10.5 * cm])
        cfop_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Clario'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.3, TR_BORDER_GREY),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [TR_WHITE, TR_LIGHT_AMBER]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(cfop_table)
        if len(cfops['alertas']) > 15:
            story.append(Paragraph(f"... e mais {len(cfops['alertas']) - 15} CFOPs (ver Detalhamento da Aderência)", s['caption']))

    # ═══════════════════════════════════════════════════════════════════════
    # 5. METODOLOGIA DE CÁLCULO
    # ═══════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("Metodologia de Cálculo de Aderência", s['heading']))
    story.append(Paragraph(
        "O <b>Score Geral de Aderência</b> é calculado através de uma média ponderada de três dimensões principais:",
        s['body']
    ))
    story.append(Spacer(1, 0.4 * cm))

    weights_data = [
        ["Dimensão", "Peso", "Cálculo"],
        ["NCM Compras", "35%", "% de pares NCM×UF (Fornecedor) com cobertura = 100%"],
        ["NCM Vendas", "35%", "% de pares NCM×UF (Cliente/Destino) com cobertura = 100%"],
        ["Municípios ISS", "30%", "% de municípios dentro do escopo de cidades cobertas"],
    ]
    weights_table = Table(weights_data, colWidths=[4 * cm, 2.5 * cm, 9 * cm])
    weights_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TR_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), TR_WHITE),
        ('ALIGN', (0, 0), (1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Clario-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Clario'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, TR_BORDER_GREY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [TR_WHITE, TR_LIGHT_GOLD]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(weights_table)
    story.append(Spacer(1, 0.5 * cm))

    score_compras = nc.get('score') or 0
    score_vendas = nv.get('score') or 0
    score_municipios = m.get('score') or 0
    score_geral = result.get('overall_score') or 0

    formula_text = f"""
    <b>Fórmula:</b><br/>
    Score Geral = (Score_Compras × 0.35) + (Score_Vendas × 0.35) + (Score_Municípios × 0.30)<br/><br/>
    <b>Exemplo deste cliente:</b><br/>
    Score Geral = ({score_compras:.1f}% × 0.35) + ({score_vendas:.1f}% × 0.35) +
                  ({score_municipios:.1f}% × 0.30) = <b>{score_geral:.1f}%</b>
    """
    story.append(Paragraph(formula_text, s['body']))
    story.append(Spacer(1, 0.5 * cm))

    criteria_text = """
    <b>Critérios de Cobertura NCM:</b><br/>
    • Cobertura = 100: NCM totalmente suportado pelo IDT naquela UF<br/>
    • Cobertura &lt; 100: Requer análise (gap parcial ou total)<br/>
    • Cobertura ausente: NCM não mapeado na base (gap crítico)<br/><br/>
    <b>Critérios de Municípios:</b><br/>
    • Atendido: Município está na lista de cidades com ISS configurado<br/>
    • Não Atendido: Município não está na cobertura padrão (decisão do time necessária)<br/>
    • Não Entendido (UF inválida): UF informada não é uma UF válida do Brasil e não pôde ser validada
    contra a lista de aderência — conta como não atendida no score<br/><br/>
    <b>Nota sobre CFOPs:</b><br/>
    CFOPs são analisados de forma qualitativa (não entram no score geral). O relatório identifica operações
    standard atendidas pelo IDT e operações não-standard que requerem customização.
    """
    story.append(Paragraph(criteria_text, s['body']))

    # ═══════════════════════════════════════════════════════════════════════
    # 6. DETALHAMENTO DA ADERÊNCIA
    # ═══════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("Detalhamento da Aderência", s['heading']))

    cfops_entrada_std, cfops_saida_std = split_cfops_by_direction(cfops.get('standard', []))

    def render_cfop_standard_list(cfop_list, title_text):
        story.append(Paragraph(title_text, s['subheading']))
        story.append(Spacer(1, 0.2 * cm))
        if not cfop_list:
            story.append(Paragraph("Nenhum CFOP standard identificado para esta direção.", s['body']))
            story.append(Spacer(1, 0.4 * cm))
            return
        rows = [[cfop, "Atendido (Standard)"] for cfop in cfop_list]
        num_cols = 3
        rows_per_col = (len(rows) + num_cols - 1) // num_cols
        grid_data = [["CFOP", "Status"] * num_cols]
        for i in range(rows_per_col):
            row = []
            for col in range(num_cols):
                idx = col * rows_per_col + i
                row.extend(rows[idx] if idx < len(rows) else ["", ""])
            grid_data.append(row)
        table = Table(grid_data, colWidths=[2 * cm, 3.5 * cm] * num_cols)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), TR_GREEN),
            ('TEXTCOLOR', (0, 0), (-1, 0), TR_WHITE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Clario-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Clario'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.3, TR_BORDER_GREY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [TR_WHITE, TR_LIGHT_TEAL]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.5 * cm))

    # ── CFOPs Atendidos - Entrada (Compras) ──
    render_cfop_standard_list(cfops_entrada_std, f"CFOPs Atendidos via Standard - Entrada ({len(cfops_entrada_std)} CFOPs)")

    # ── NCM Compras ──
    story.append(Paragraph("NCM Compras - Análise Detalhada", s['subheading']))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        f"<b>{nc.get('covered', 0)}</b> de <b>{nc.get('total_pairs', 0)}</b> pares NCM×UF cobertos "
        f"({(nc.get('score') or 0):.1f}%)", s['body']
    ))
    story.append(Spacer(1, 0.3 * cm))

    uf_summary_c = nc.get('uf_summary', {})
    if uf_summary_c:
        uf_data = [["UF", "Score (%)", "Cobertos", "Gap", "Total NCMs"]]
        for uf, stats in sorted(uf_summary_c.items()):
            uf_data.append([uf, f"{stats['score']:.1f}%", str(stats['covered']), str(stats['gap']), str(stats['total'])])
        uf_table = Table(uf_data, colWidths=[2.5 * cm, 3.5 * cm, 3.5 * cm, 3 * cm, 3.5 * cm])
        uf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), TR_GREEN),
            ('TEXTCOLOR', (0, 0), (-1, 0), TR_WHITE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Clario-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Clario'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, TR_BORDER_GREY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [TR_WHITE, TR_LIGHT_GOLD]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ]))
        story.append(uf_table)

    def render_ncm_detail_table(items, title_text):
        story.append(PageBreak())
        story.append(Paragraph(title_text, s['subsub']))
        story.append(Spacer(1, 0.2 * cm))
        rows = []
        for item in items:
            desc = item.get('Descricao', '')
            cfop_val = item.get('CFOP', '') or '—'
            cfop_status = cfop_standard_status(item.get('CFOP'), non_standard_cfops)
            cov = item.get('Cobertura', '')
            cov_str = f"{cov}%" if cov not in (None, '') else ("100%" if item.get('Coberto') else "N/A")
            rows.append([item.get('NCM', ''), item.get('UF', ''), desc, cfop_val, cfop_status, cov_str])
        create_paginated_table(
            data_rows=rows,
            columns=["NCM", "UF", "Descrição", "CFOP", "Atende via Standard", "Cob.(%)"],
            col_widths=[2.2 * cm, 1.2 * cm, 5.8 * cm, 1.8 * cm, 3 * cm, 1.9 * cm],
            title="", story=story, heading_style=s['heading'], items_per_page=28
        )

    if nc.get('gaps'):
        render_ncm_detail_table(nc['gaps'], f"NCM Compras - TODOS os Gaps ({len(nc['gaps'])} pares)")

    # ── NCM Vendas ──
    story.append(PageBreak())

    # ── CFOPs Atendidos - Saída (Vendas) ──
    render_cfop_standard_list(cfops_saida_std, f"CFOPs Atendidos via Standard - Saída ({len(cfops_saida_std)} CFOPs)")

    story.append(Paragraph("NCM Vendas - Análise Detalhada", s['subheading']))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        f"<b>{nv.get('covered', 0)}</b> de <b>{nv.get('total_pairs', 0)}</b> pares NCM×UF cobertos "
        f"({(nv.get('score') or 0):.1f}%)", s['body']
    ))
    story.append(Spacer(1, 0.3 * cm))

    uf_summary_v = nv.get('uf_summary', {})
    if uf_summary_v:
        uf_data_v = [["UF", "Score (%)", "Cobertos", "Gap", "Total NCMs"]]
        for uf, stats in sorted(uf_summary_v.items()):
            uf_data_v.append([uf, f"{stats['score']:.1f}%", str(stats['covered']), str(stats['gap']), str(stats['total'])])
        uf_table_v = Table(uf_data_v, colWidths=[2.5 * cm, 3.5 * cm, 3.5 * cm, 3 * cm, 3.5 * cm])
        uf_table_v.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), TR_GREEN),
            ('TEXTCOLOR', (0, 0), (-1, 0), TR_WHITE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Clario-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Clario'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, TR_BORDER_GREY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [TR_WHITE, TR_LIGHT_GOLD]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ]))
        story.append(uf_table_v)

    if nv.get('gaps'):
        render_ncm_detail_table(nv['gaps'], f"NCM Vendas - TODOS os Gaps ({len(nv['gaps'])} pares)")

    # ── Municípios ──
    story.append(PageBreak())
    story.append(Paragraph("Municípios ISS - Análise Detalhada", s['heading']))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        f"<b>{len(m.get('in_scope', []))} municípios</b> cobertos pelo IDT · "
        f"<b>{len(m.get('out_of_scope', []))} municípios</b> com GAP (não cobertos) · "
        f"<b>{len(m.get('invalid', []))} municípios</b> não entendidos (UF inválida) "
        f"({(m.get('score') or 0):.1f}% cobertura)",
        s['body']
    ))
    story.append(Spacer(1, 0.5 * cm))

    if m.get('out_of_scope'):
        story.append(Paragraph(f"Municípios com GAP - Não Cobertos ({len(m['out_of_scope'])} cidades)", s['subsub']))
        story.append(Spacer(1, 0.2 * cm))
        gap_rows = [[city, "Não Coberto"] for city in sorted(m['out_of_scope'])]
        create_paginated_table(
            data_rows=gap_rows, columns=["Município (UF)", "Status"],
            col_widths=[12 * cm, 3.5 * cm], title="", story=story,
            heading_style=s['heading'], items_per_page=40
        )
    else:
        story.append(Paragraph("Municípios com GAP - Não Cobertos", s['subsub']))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(
            "Nenhum município fora do escopo — todos os municípios informados estão cobertos pelo IDT.",
            s['body']
        ))
        story.append(Spacer(1, 0.5 * cm))

    if m.get('invalid'):
        story.append(Paragraph(f"Municípios Não Entendidos - UF Inválida ({len(m['invalid'])} cidades)", s['subsub']))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(
            "Linhas cuja UF informada não corresponde a uma UF válida do Brasil (ex.: \"NI\", \"NA\" ou "
            "código incorreto). Não puderam ser validadas contra a lista de aderência e contam como "
            "não atendidas no score.",
            s['body']
        ))
        story.append(Spacer(1, 0.2 * cm))
        invalid_rows = [[city, "Não Entendido"] for city in sorted(m['invalid'])]
        create_paginated_table(
            data_rows=invalid_rows, columns=["Município (UF)", "Status"],
            col_widths=[12 * cm, 3.5 * cm], title="", story=story,
            heading_style=s['heading'], items_per_page=40
        )
        story.append(Spacer(1, 0.5 * cm))

    if m.get('in_scope'):
        story.append(PageBreak())
        story.append(Paragraph(f"Municípios Dentro do Escopo IDT ({len(m['in_scope'])} cidades)", s['subsub']))
        story.append(Spacer(1, 0.2 * cm))
        in_rows = [[city, "Coberto"] for city in sorted(m['in_scope'])]
        create_paginated_table(
            data_rows=in_rows, columns=["Município (UF)", "Status"],
            col_widths=[12 * cm, 3.5 * cm], title="", story=story,
            heading_style=s['heading'], items_per_page=40
        )

    # ── CST Coverage (apêndice) ──
    story.append(PageBreak())
    story.append(Paragraph("CST Coverage - Cobertura por Tributo", s['heading']))
    story.append(Spacer(1, 0.3 * cm))

    if cst_cov:
        for tributo, csts_dict in sorted(cst_cov.items()):
            total_csts = len(csts_dict)
            atendidos = sum(1 for v in csts_dict.values() if v)
            pct = (atendidos / total_csts * 100) if total_csts > 0 else 0

            story.append(Paragraph(f"<b>{tributo}</b> - {atendidos}/{total_csts} CSTs atendidos ({pct:.0f}%)", s['subsub']))
            story.append(Spacer(1, 0.2 * cm))

            cst_rows = [[cst_code, "Sim" if ok else "Não"] for cst_code, ok in sorted(csts_dict.items())]
            num_cols = 4
            rows_per_col = (len(cst_rows) + num_cols - 1) // num_cols
            grid_data = [["CST", "Atendido"] * num_cols]
            for i in range(rows_per_col):
                row = []
                for col in range(num_cols):
                    idx = col * rows_per_col + i
                    row.extend(cst_rows[idx] if idx < len(cst_rows) else ["", ""])
                grid_data.append(row)

            cst_table = Table(grid_data, colWidths=[2 * cm, 1.8 * cm] * num_cols)
            cst_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), TR_ORANGE),
                ('TEXTCOLOR', (0, 0), (-1, 0), TR_WHITE),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Clario-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Clario'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.3, TR_BORDER_GREY),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(cst_table)
            story.append(Spacer(1, 0.5 * cm))
    else:
        story.append(Paragraph("Nenhuma informação de CST disponível.", s['body']))

    # ── CFOPs completos (apêndice) ──
    story.append(PageBreak())
    if cfops.get('alertas'):
        story.append(Paragraph(f"CFOPs Não-Standard - TODOS os Alertas ({len(cfops['alertas'])} operações)", s['heading']))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(
            "Os CFOPs listados abaixo requerem customização do IDT — não são atendidos pela configuração standard:",
            s['body']
        ))
        story.append(Spacer(1, 0.3 * cm))
        cfop_alert_rows = [[a.get('CFOP', ''), a.get('Tipo', ''), a.get('Mensagem', '')] for a in cfops['alertas']]
        create_paginated_table(
            data_rows=cfop_alert_rows, columns=["CFOP", "Tipo", "Mensagem"],
            col_widths=[2.5 * cm, 3.5 * cm, 9.5 * cm], title="", story=story,
            heading_style=s['heading'], items_per_page=25
        )

    if cfops.get('standard'):
        story.append(PageBreak())
        story.append(Paragraph(f"CFOPs Standard - Operações Atendidas ({len(cfops['standard'])} CFOPs)", s['heading']))
        story.append(Spacer(1, 0.2 * cm))
        std_rows = [[cfop, "Atendido (Standard)"] for cfop in sorted(cfops['standard'])]
        create_paginated_table(
            data_rows=std_rows, columns=["CFOP", "Status"],
            col_widths=[3 * cm, 12.5 * cm], title="", story=story,
            heading_style=s['heading'], items_per_page=35
        )

    # ── Footer ──
    story.append(Spacer(1, 1.5 * cm))
    footer_style = ParagraphStyle('Footer', fontName='Clario-Light', fontSize=8,
                                   textColor=colors.grey, alignment=TA_CENTER)
    story.append(Paragraph(
        f"Relatório gerado automaticamente pelo IDT Analyzer<br/>"
        f"Thomson Reuters | {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
        footer_style
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


if __name__ == "__main__":
    print("PDF Generator module loaded")
    print("Use generate_pdf(result) to create a PDF report")
