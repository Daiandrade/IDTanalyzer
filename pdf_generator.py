"""
PDF Executive Report Generator for IDT Analyzer
Generates a visual, executive-level PDF report
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie

# Thomson Reuters Brand Colors (Global Constants)
TR_GREEN = colors.HexColor('#123015')
TR_ORANGE = colors.HexColor('#D64000')


def score_color(score):
    """Return color based on score"""
    if score is None:
        return colors.grey
    if score >= 80:
        return colors.green
    if score >= 50:
        return colors.orange
    return colors.red


def create_score_card(score, label, width=4*cm, height=2.5*cm):
    """Create a visual score card"""
    drawing = Drawing(width, height)

    # Background rectangle
    bg_color = score_color(score)
    rect = Rect(0, 0, width, height, fillColor=bg_color, strokeColor=colors.white, strokeWidth=2)
    drawing.add(rect)

    # Score text (simplified - would need more complex text rendering)
    return drawing


def create_paginated_table(data_rows, columns, col_widths, title, story, heading_style, items_per_page=25):
    """
    Cria tabela paginada para listas longas.

    Args:
        data_rows: Lista de listas com dados (sem header)
        columns: Lista de headers (ex: ["<b>NCM</b>", "<b>UF</b>"])
        col_widths: Lista de larguras de colunas (ex: [3*cm, 2*cm])
        title: Título da seção (se vazio, não adiciona)
        story: Story do PDF (para append)
        heading_style: Estilo de título
        items_per_page: Quantos itens por página
    """
    if not data_rows:
        return

    # Header (se título fornecido)
    if title:
        story.append(Paragraph(title, heading_style))
        story.append(Spacer(1, 0.3*cm))

    # Dividir em páginas
    total_items = len(data_rows)
    num_pages = (total_items + items_per_page - 1) // items_per_page

    for page_num in range(num_pages):
        start_idx = page_num * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)

        # Subtítulo de paginação
        if num_pages > 1:
            italic_style = ParagraphStyle('Italic', fontSize=9, textColor=colors.grey, alignment=TA_CENTER)
            story.append(Paragraph(
                f"<i>Página {page_num + 1} de {num_pages} (itens {start_idx + 1}-{end_idx} de {total_items})</i>",
                italic_style
            ))
            story.append(Spacer(1, 0.2*cm))

        # Criar tabela desta página
        page_data = [columns] + data_rows[start_idx:end_idx]

        table = Table(page_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), TR_ORANGE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))

        story.append(table)

        # PageBreak entre páginas de dados (exceto última)
        if page_num < num_pages - 1:
            story.append(PageBreak())


def generate_pdf(result: dict, filename: str = "relatorio_idt.pdf", cliente_nome: str = None) -> bytes:
    """
    Generate executive PDF report with Thomson Reuters template
    Returns: PDF bytes
    """
    buffer = io.BytesIO()

    # Document setup
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2.5*cm,
        bottomMargin=2*cm
    )

    # Styles - Thomson Reuters Theme
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=TR_GREEN,
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=TR_GREEN,
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )

    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=TR_ORANGE,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        fontName='Helvetica'
    )

    # Build content
    story = []

    # ── Title Page ──
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("IDT · Relatório de Aderência", title_style))
    story.append(Paragraph("Análise de Pré-Diagnóstico Fiscal", styles['Heading2']))
    story.append(Spacer(1, 0.5*cm))

    general = result.get("general", {})

    # Client info box - Thomson Reuters style
    # Usa nome customizado se fornecido, senão usa segmento do arquivo
    nome_cliente = cliente_nome if cliente_nome else general.get("segmento", "N/A")

    client_info = [
        ["Cliente:", nome_cliente],
        ["Segmento:", general.get("segmento", "N/A")],
        ["Estados:", general.get("estados", "N/A")],
        ["Atividade:", general.get("atividade", "N/A")],
        ["Data da Análise:", datetime.now().strftime("%d/%m/%Y")],
    ]

    client_table = Table(client_info, colWidths=[4.5*cm, 11*cm])
    client_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), TR_GREEN),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    story.append(client_table)
    story.append(Spacer(1, 1*cm))

    # ── Scores Summary ──
    story.append(Paragraph("Resumo Executivo", heading_style))
    story.append(Spacer(1, 0.3*cm))

    scores_data = [
        ["<b>Dimensão</b>", "<b>Score (%)</b>", "<b>Status</b>"],
        [
            "Score Geral",
            f"{result.get('overall_score', 0):.1f}%" if result.get('overall_score') else "N/A",
            get_status_text(result.get('overall_score'))
        ],
        [
            "NCM Compras",
            f"{result['ncm_compras'].get('score', 0):.1f}%" if result['ncm_compras'].get('score') else "N/A",
            get_status_text(result['ncm_compras'].get('score'))
        ],
        [
            "NCM Vendas",
            f"{result['ncm_vendas'].get('score', 0):.1f}%" if result['ncm_vendas'].get('score') else "N/A",
            get_status_text(result['ncm_vendas'].get('score'))
        ],
        [
            "Municípios ISS",
            f"{result['municipios'].get('score', 0):.1f}%" if result['municipios'].get('score') else "N/A",
            get_status_text(result['municipios'].get('score'))
        ],
    ]

    scores_table = Table(scores_data, colWidths=[6*cm, 4*cm, 5.5*cm])
    scores_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TR_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))

    story.append(scores_table)
    story.append(Spacer(1, 0.8*cm))

    # ── Key Findings ──
    story.append(Paragraph("Principais Achados", heading_style))
    story.append(Spacer(1, 0.2*cm))

    findings = []

    # NCM Gaps
    nc = result['ncm_compras']
    nv = result['ncm_vendas']
    if nc.get('gaps') or nv.get('gaps'):
        total_gaps = len(nc.get('gaps', [])) + len(nv.get('gaps', []))
        findings.append(f"• <b>{total_gaps} pares NCM×UF</b> não possuem cobertura completa")

    # Municípios com GAP (não cobertos)
    m = result['municipios']
    if m.get('gaps'):
        findings.append(f"• <b>{len(m['gaps'])} municípios</b> não estão cobertos pela lista de aderência (GAPs identificados)")

    # CFOPs não-standard
    cfops = result.get('cfops', {})
    if cfops.get('alertas'):
        findings.append(f"• <b>{len(cfops['alertas'])} CFOPs</b> requerem customização (operações não-standard)")

    # Positive findings
    nc_score = nc.get('score')
    if nc_score is not None and nc_score >= 90:
        findings.append(f"• ✅ Excelente cobertura em <b>NCM Compras</b> ({nc_score:.1f}%)")
    nv_score = nv.get('score')
    if nv_score is not None and nv_score >= 90:
        findings.append(f"• ✅ Excelente cobertura em <b>NCM Vendas</b> ({nv_score:.1f}%)")

    for finding in findings:
        story.append(Paragraph(finding, body_style))
        story.append(Spacer(1, 0.2*cm))

    # ── NOVA SEÇÃO: Itens Não Atendidos - Resumo Consolidado ──
    story.append(PageBreak())
    story.append(Paragraph("❌ Itens Não Atendidos - Resumo Consolidado", heading_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "Esta seção consolida todos os itens que requerem atenção por não estarem completamente cobertos pelo IDT standard:",
        body_style
    ))
    story.append(Spacer(1, 0.5*cm))

    # NCMs Não Atendidos
    if nc.get('gaps') or nv.get('gaps'):
        story.append(Paragraph("📦 NCMs Não Atendidos", subheading_style))
        story.append(Spacer(1, 0.2*cm))

        total_ncm_gaps = len(nc.get('gaps', [])) + len(nv.get('gaps', []))
        story.append(Paragraph(
            f"<b>{total_ncm_gaps} pares NCM×UF</b> identificados sem cobertura completa:",
            body_style
        ))
        story.append(Spacer(1, 0.3*cm))

        # NCMs Compras não atendidos
        if nc.get('gaps'):
            story.append(Paragraph(f"<b>Compras ({len(nc['gaps'])} gaps):</b>", body_style))
            ncm_c_rows = []
            for gap in nc['gaps'][:10]:  # Primeiros 10
                desc = gap.get('Descricao', '')[:50] + '...' if len(gap.get('Descricao', '')) > 50 else gap.get('Descricao', '')
                cov = gap.get('Cobertura', '')
                cov_str = f"{cov}%" if cov is not None and cov != '' else "N/A"
                ncm_c_rows.append([
                    gap.get('NCM', ''),
                    gap.get('UF', ''),
                    desc,
                    cov_str
                ])

            if ncm_c_rows:
                ncm_c_table = Table(ncm_c_rows, colWidths=[2.5*cm, 1.5*cm, 9*cm, 2.5*cm])
                ncm_c_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
                    ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#fff5f5')]),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(ncm_c_table)
                if len(nc['gaps']) > 10:
                    story.append(Paragraph(
                        f"<i>... e mais {len(nc['gaps']) - 10} itens (ver detalhamento completo nas próximas páginas)</i>",
                        ParagraphStyle('Italic', fontSize=8, textColor=colors.grey)
                    ))
                story.append(Spacer(1, 0.3*cm))

        # NCMs Vendas não atendidos
        if nv.get('gaps'):
            story.append(Paragraph(f"<b>Vendas ({len(nv['gaps'])} gaps):</b>", body_style))
            ncm_v_rows = []
            for gap in nv['gaps'][:10]:  # Primeiros 10
                desc = gap.get('Descricao', '')[:50] + '...' if len(gap.get('Descricao', '')) > 50 else gap.get('Descricao', '')
                cov = gap.get('Cobertura', '')
                cov_str = f"{cov}%" if cov is not None and cov != '' else "N/A"
                ncm_v_rows.append([
                    gap.get('NCM', ''),
                    gap.get('UF', ''),
                    desc,
                    cov_str
                ])

            if ncm_v_rows:
                ncm_v_table = Table(ncm_v_rows, colWidths=[2.5*cm, 1.5*cm, 9*cm, 2.5*cm])
                ncm_v_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
                    ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#fff5f5')]),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(ncm_v_table)
                if len(nv['gaps']) > 10:
                    story.append(Paragraph(
                        f"<i>... e mais {len(nv['gaps']) - 10} itens (ver detalhamento completo nas próximas páginas)</i>",
                        ParagraphStyle('Italic', fontSize=8, textColor=colors.grey)
                    ))
                story.append(Spacer(1, 0.5*cm))

    # Municípios Não Atendidos
    if m.get('out_of_scope'):
        story.append(Paragraph("🏙 Municípios Não Atendidos", subheading_style))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(
            f"<b>{len(m['out_of_scope'])} municípios</b> fora do escopo de 834 cidades cobertas pelo IDT:",
            body_style
        ))
        story.append(Spacer(1, 0.3*cm))

        # Lista primeiros 20 municípios
        mun_rows = [[city] for city in sorted(m['out_of_scope'])[:20]]
        if mun_rows:
            # 3 colunas para economizar espaço
            num_cols = 3
            rows_per_col = (len(mun_rows) + num_cols - 1) // num_cols
            grid_data = []
            for i in range(rows_per_col):
                row = []
                for col in range(num_cols):
                    idx = col * rows_per_col + i
                    if idx < len(mun_rows):
                        row.append(mun_rows[idx][0])
                    else:
                        row.append("")
                grid_data.append(row)

            mun_table = Table(grid_data, colWidths=[5.2*cm] * num_cols)
            mun_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(mun_table)
            if len(m['out_of_scope']) > 20:
                story.append(Paragraph(
                    f"<i>... e mais {len(m['out_of_scope']) - 20} municípios (ver detalhamento completo)</i>",
                    ParagraphStyle('Italic', fontSize=8, textColor=colors.grey)
                ))
            story.append(Spacer(1, 0.5*cm))

    # CSTs Não Atendidos
    cst_cov = result.get('cst_coverage', {})
    if cst_cov:
        cst_nao_atendidos = {}
        for tributo, csts_dict in cst_cov.items():
            nao_atendidos = {cst: atendido for cst, atendido in csts_dict.items() if not atendido}
            if nao_atendidos:
                cst_nao_atendidos[tributo] = nao_atendidos

        if cst_nao_atendidos:
            story.append(Paragraph("📋 CSTs Não Atendidos", subheading_style))
            story.append(Spacer(1, 0.2*cm))
            for tributo, csts_dict in sorted(cst_nao_atendidos.items()):
                csts_list = ", ".join(sorted(csts_dict.keys()))
                story.append(Paragraph(
                    f"<b>{tributo}:</b> {csts_list}",
                    body_style
                ))
            story.append(Spacer(1, 0.5*cm))

    # CFOPs Não Atendidos
    if cfops.get('alertas'):
        story.append(Paragraph("⚠️ CFOPs Não-Standard", subheading_style))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(
            f"<b>{len(cfops['alertas'])} CFOPs</b> requerem customização (não são operações standard):",
            body_style
        ))
        story.append(Spacer(1, 0.3*cm))

        cfop_rows = []
        for alerta in cfops['alertas'][:15]:  # Primeiros 15
            cfop_rows.append([
                alerta.get('CFOP', ''),
                alerta.get('Tipo', ''),
                alerta.get('Mensagem', '')[:60] + '...' if len(alerta.get('Mensagem', '')) > 60 else alerta.get('Mensagem', '')
            ])

        if cfop_rows:
            cfop_table = Table(cfop_rows, colWidths=[2*cm, 3*cm, 10.5*cm])
            cfop_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
                ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#fff5f5')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(cfop_table)
            if len(cfops['alertas']) > 15:
                story.append(Paragraph(
                    f"<i>... e mais {len(cfops['alertas']) - 15} CFOPs (ver detalhamento completo)</i>",
                    ParagraphStyle('Italic', fontSize=8, textColor=colors.grey)
                ))

    # ── NOVA SEÇÃO: Metodologia de Cálculo ──
    story.append(PageBreak())
    story.append(Paragraph("Metodologia de Cálculo de Aderência", heading_style))
    story.append(Spacer(1, 0.3*cm))

    methodology_text = """
    O <b>Score Geral de Aderência</b> é calculado através de uma média ponderada de três dimensões principais:
    """
    story.append(Paragraph(methodology_text, body_style))
    story.append(Spacer(1, 0.4*cm))

    # Tabela de pesos
    weights_data = [
        ["<b>Dimensão</b>", "<b>Peso</b>", "<b>Cálculo</b>"],
        [
            "NCM Compras",
            "35%",
            "% de pares NCM×UF (Fornecedor) com cobertura = 100%"
        ],
        [
            "NCM Vendas",
            "35%",
            "% de pares NCM×UF (Cliente/Destino) com cobertura = 100%"
        ],
        [
            "Municípios ISS",
            "30%",
            "% de municípios dentro do escopo de 834 cidades cobertas"
        ],
    ]

    weights_table = Table(weights_data, colWidths=[4*cm, 2.5*cm, 9*cm])
    weights_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TR_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(weights_table)
    story.append(Spacer(1, 0.5*cm))

    # Fórmula com exemplo do cliente
    # Garantir que None seja convertido para 0
    score_compras = result['ncm_compras'].get('score') or 0
    score_vendas = result['ncm_vendas'].get('score') or 0
    score_municipios = result['municipios'].get('score') or 0
    score_geral = result.get('overall_score') or 0

    formula_text = f"""
    <b>Fórmula:</b><br/>
    Score Geral = (Score_Compras × 0.35) + (Score_Vendas × 0.35) + (Score_Municípios × 0.30)<br/><br/>

    <b>Exemplo deste cliente:</b><br/>
    Score Geral = ({score_compras:.1f}% × 0.35) +
                  ({score_vendas:.1f}% × 0.35) +
                  ({score_municipios:.1f}% × 0.30) =
                  <b>{score_geral:.1f}%</b>
    """
    story.append(Paragraph(formula_text, body_style))
    story.append(Spacer(1, 0.5*cm))

    # Critérios de cobertura
    criteria_text = """
    <b>Critérios de Cobertura NCM:</b><br/>
    • Cobertura = 100: NCM totalmente suportado pelo IDT naquela UF<br/>
    • Cobertura &lt; 100: Requer análise (gap parcial ou total)<br/>
    • Cobertura ausente: NCM não mapeado na base (gap crítico)<br/><br/>

    <b>Critérios de Municípios:</b><br/>
    • In-scope: Município está na lista de 834 cidades com ISS configurado<br/>
    • Out-of-scope: Município não está na cobertura padrão (decisão do time necessária)<br/><br/>

    <b>Nota sobre CFOPs:</b><br/>
    CFOPs são analisados de forma qualitativa (não entram no score geral). O relatório identifica operações
    standard atendidas pelo IDT e operações não-standard que requerem customização.
    """
    story.append(Paragraph(criteria_text, body_style))

    # ── NCM Details ──
    story.append(PageBreak())
    story.append(Paragraph("Detalhamento de NCM", heading_style))

    # ── NCM Compras: Análise Detalhada ──
    story.append(Paragraph("NCM Compras - Análise Detalhada", subheading_style))
    story.append(Spacer(1, 0.3*cm))

    # Score geral
    subsub_style = ParagraphStyle('SubSub', fontSize=11, textColor=TR_GREEN, fontName='Helvetica-Bold')
    story.append(Paragraph("Score de Cobertura por UF do Fornecedor", subsub_style))
    nc_score = nc.get('score') or 0
    story.append(Paragraph(
        f"<b>{nc.get('covered', 0)}</b> de <b>{nc.get('total_pairs', 0)}</b> pares NCM×UF cobertos " +
        f"({nc_score:.1f}%)",
        body_style
    ))
    story.append(Spacer(1, 0.3*cm))

    # Tabela de Score por UF
    uf_summary_c = nc.get('uf_summary', {})
    if uf_summary_c:
        uf_data = [["<b>UF</b>", "<b>Score (%)</b>", "<b>Cobertos</b>", "<b>Gap</b>", "<b>Total NCMs</b>", "<b>Status</b>"]]
        for uf, stats in sorted(uf_summary_c.items()):
            status_emoji = "✅" if stats["score"] == 100 else ("⚠️" if stats["score"] >= 50 else "❌")
            uf_data.append([
                uf,
                f"{stats['score']:.1f}%",
                str(stats['covered']),
                str(stats['gap']),
                str(stats['total']),
                status_emoji
            ])

        uf_table = Table(uf_data, colWidths=[2*cm, 3*cm, 3*cm, 2.5*cm, 3*cm, 2*cm])
        uf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), TR_GREEN),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ]))
        story.append(uf_table)

    # ── NCM Compras: TODOS os gaps ──
    if nc.get('gaps'):
        story.append(PageBreak())
        subsub_style = ParagraphStyle('SubSub', fontSize=11, textColor=TR_GREEN, fontName='Helvetica-Bold')
        story.append(Paragraph(f"NCM Compras - TODOS os Gaps ({len(nc['gaps'])} pares)", subsub_style))
        story.append(Spacer(1, 0.2*cm))

        gap_rows = []
        for gap in nc['gaps']:
            desc = gap.get('Descricao', '')
            desc_truncated = desc[:60] + '...' if len(desc) > 60 else desc
            cov = gap.get('Cobertura', '')
            cov_str = f"{cov}%" if cov is not None and cov != '' else "N/A"
            gap_rows.append([
                gap.get('NCM', ''),
                gap.get('UF', ''),
                desc_truncated,
                cov_str
            ])

        create_paginated_table(
            data_rows=gap_rows,
            columns=["<b>NCM</b>", "<b>UF</b>", "<b>Descrição</b>", "<b>Cob.(%)</b>"],
            col_widths=[3*cm, 2*cm, 9*cm, 1.5*cm],
            title="",
            story=story,
            heading_style=heading_style,
            items_per_page=30
        )

    # ── NCM Compras: TODOS os itens COBERTOS (100%) ──
    covered_items_c = [item for item in nc.get('detail', []) if item.get('Coberto', False)]
    if covered_items_c:
        story.append(PageBreak())
        subsub_style = ParagraphStyle('SubSub', fontSize=11, textColor=TR_GREEN, fontName='Helvetica-Bold')
        story.append(Paragraph(f"NCM Compras - Itens com Cobertura Completa ({len(covered_items_c)} pares)", subsub_style))
        story.append(Spacer(1, 0.2*cm))

        covered_rows = []
        for item in covered_items_c:
            desc = item.get('Descricao', '')
            desc_truncated = desc[:60] + '...' if len(desc) > 60 else desc
            covered_rows.append([
                item.get('NCM', ''),
                item.get('UF', ''),
                desc_truncated,
                "✅ 100%"
            ])

        create_paginated_table(
            data_rows=covered_rows,
            columns=["<b>NCM</b>", "<b>UF</b>", "<b>Descrição</b>", "<b>Status</b>"],
            col_widths=[3*cm, 2*cm, 9*cm, 1.5*cm],
            title="",
            story=story,
            heading_style=heading_style,
            items_per_page=30
        )

    # ── NCM Vendas: Análise Detalhada ──
    story.append(PageBreak())
    story.append(Paragraph("NCM Vendas - Análise Detalhada", subheading_style))
    story.append(Spacer(1, 0.3*cm))

    # Score geral
    subsub_style = ParagraphStyle('SubSub', fontSize=11, textColor=TR_GREEN, fontName='Helvetica-Bold')
    story.append(Paragraph("Score de Cobertura por UF do Cliente/Destino", subsub_style))
    nv_score = nv.get('score') or 0
    story.append(Paragraph(
        f"<b>{nv.get('covered', 0)}</b> de <b>{nv.get('total_pairs', 0)}</b> pares NCM×UF cobertos " +
        f"({nv_score:.1f}%)",
        body_style
    ))
    story.append(Spacer(1, 0.3*cm))

    # Tabela de Score por UF
    uf_summary_v = nv.get('uf_summary', {})
    if uf_summary_v:
        uf_data_v = [["<b>UF</b>", "<b>Score (%)</b>", "<b>Cobertos</b>", "<b>Gap</b>", "<b>Total NCMs</b>", "<b>Status</b>"]]
        for uf, stats in sorted(uf_summary_v.items()):
            status_emoji = "✅" if stats["score"] == 100 else ("⚠️" if stats["score"] >= 50 else "❌")
            uf_data_v.append([
                uf,
                f"{stats['score']:.1f}%",
                str(stats['covered']),
                str(stats['gap']),
                str(stats['total']),
                status_emoji
            ])

        uf_table_v = Table(uf_data_v, colWidths=[2*cm, 3*cm, 3*cm, 2.5*cm, 3*cm, 2*cm])
        uf_table_v.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), TR_GREEN),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ]))
        story.append(uf_table_v)

    # ── NCM Vendas: TODOS os gaps ──
    if nv.get('gaps'):
        story.append(PageBreak())
        story.append(Paragraph(f"NCM Vendas - TODOS os Gaps ({len(nv['gaps'])} pares)", subsub_style))
        story.append(Spacer(1, 0.2*cm))

        gap_rows_v = []
        for gap in nv['gaps']:
            desc = gap.get('Descricao', '')
            desc_truncated = desc[:60] + '...' if len(desc) > 60 else desc
            cov = gap.get('Cobertura', '')
            cov_str = f"{cov}%" if cov is not None and cov != '' else "N/A"
            gap_rows_v.append([
                gap.get('NCM', ''),
                gap.get('UF', ''),
                desc_truncated,
                cov_str
            ])

        create_paginated_table(
            data_rows=gap_rows_v,
            columns=["<b>NCM</b>", "<b>UF</b>", "<b>Descrição</b>", "<b>Cob.(%)</b>"],
            col_widths=[3*cm, 2*cm, 9*cm, 1.5*cm],
            title="",
            story=story,
            heading_style=heading_style,
            items_per_page=30
        )

    # ── NCM Vendas: TODOS os itens COBERTOS (100%) ──
    covered_items_v = [item for item in nv.get('detail', []) if item.get('Coberto', False)]
    if covered_items_v:
        story.append(PageBreak())
        story.append(Paragraph(f"NCM Vendas - Itens com Cobertura Completa ({len(covered_items_v)} pares)", subsub_style))
        story.append(Spacer(1, 0.2*cm))

        covered_rows_v = []
        for item in covered_items_v:
            desc = item.get('Descricao', '')
            desc_truncated = desc[:60] + '...' if len(desc) > 60 else desc
            covered_rows_v.append([
                item.get('NCM', ''),
                item.get('UF', ''),
                desc_truncated,
                "✅ 100%"
            ])

        create_paginated_table(
            data_rows=covered_rows_v,
            columns=["<b>NCM</b>", "<b>UF</b>", "<b>Descrição</b>", "<b>Status</b>"],
            col_widths=[3*cm, 2*cm, 9*cm, 1.5*cm],
            title="",
            story=story,
            heading_style=heading_style,
            items_per_page=30
        )

    # ── Municípios ISS: Detalhamento completo ──
    story.append(PageBreak())
    story.append(Paragraph("Municípios ISS - Análise Detalhada", heading_style))
    story.append(Spacer(1, 0.3*cm))

    m = result['municipios']

    # Resumo
    m_score = m.get('score') or 0
    story.append(Paragraph(
        f"<b>{len(m.get('in_scope', []))} municípios</b> cobertos pelo IDT · " +
        f"<b>{len(m.get('gaps', []))} municípios</b> com GAP (não cobertos) ({m_score:.1f}% cobertura)",
        body_style
    ))
    story.append(Spacer(1, 0.5*cm))

    # Municípios com GAP (não cobertos) - mais crítico, vem primeiro
    if m.get('gaps'):
        story.append(Paragraph(f"❌ Municípios com GAP - Não Cobertos ({len(m['gaps'])} cidades)", subsub_style))
        story.append(Spacer(1, 0.2*cm))

        gap_rows = [[city, "❌ Não Coberto"] for city in sorted(m['gaps'])]
        create_paginated_table(
            data_rows=gap_rows,
            columns=["<b>Município (UF)</b>", "<b>Status</b>"],
            col_widths=[12*cm, 3.5*cm],
            title="",
            story=story,
            heading_style=heading_style,
            items_per_page=40
        )

    # Municípios DENTRO do escopo
    if m.get('in_scope'):
        story.append(PageBreak())
        story.append(Paragraph(f"Municípios Dentro do Escopo IDT ({len(m['in_scope'])} cidades)", subsub_style))
        story.append(Spacer(1, 0.2*cm))

        in_rows = [[city, "✅ Coberto"] for city in sorted(m['in_scope'])]
        create_paginated_table(
            data_rows=in_rows,
            columns=["<b>Município (UF)</b>", "<b>Status</b>"],
            col_widths=[12*cm, 3.5*cm],
            title="",
            story=story,
            heading_style=heading_style,
            items_per_page=40
        )

    # ── CST Coverage ──
    story.append(PageBreak())
    story.append(Paragraph("CST Coverage - Cobertura por Tributo", heading_style))
    story.append(Spacer(1, 0.3*cm))

    cst_cov = result.get('cst_coverage', {})
    if cst_cov:
        for tributo, csts_dict in sorted(cst_cov.items()):
            total_csts = len(csts_dict)
            atendidos = sum(1 for v in csts_dict.values() if v)
            pct = (atendidos / total_csts * 100) if total_csts > 0 else 0

            story.append(Paragraph(
                f"<b>{tributo}</b> - {atendidos}/{total_csts} CSTs atendidos ({pct:.0f}%)",
                subsub_style
            ))
            story.append(Spacer(1, 0.2*cm))

            # Criar tabela de CSTs em grid (4 colunas para economizar espaço)
            cst_rows = []
            for cst_code, is_covered in sorted(csts_dict.items()):
                status = "✅ Sim" if is_covered else "❌ Não"
                cst_rows.append([cst_code, status])

            # Dividir em 4 colunas
            num_cols = 4
            rows_per_col = (len(cst_rows) + num_cols - 1) // num_cols

            grid_data = [["<b>CST</b>", "<b>Atendido</b>"] * num_cols]
            for i in range(rows_per_col):
                row = []
                for col in range(num_cols):
                    idx = col * rows_per_col + i
                    if idx < len(cst_rows):
                        row.extend(cst_rows[idx])
                    else:
                        row.extend(["", ""])
                grid_data.append(row)

            cst_table = Table(grid_data, colWidths=[2*cm, 1.8*cm] * num_cols)
            cst_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), TR_ORANGE),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))

            story.append(cst_table)
            story.append(Spacer(1, 0.5*cm))
    else:
        story.append(Paragraph("Nenhuma informação de CST disponível.", body_style))

    story.append(PageBreak())

    # ── CFOPs: TODOS os alertas ──
    if cfops.get('alertas'):
        story.append(Paragraph(f"⚠️ CFOPs Não-Standard - TODOS os Alertas ({len(cfops['alertas'])} operações)", heading_style))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(
            "Os CFOPs listados abaixo requerem customização do IDT — não são atendidos pela configuração standard:",
            body_style
        ))
        story.append(Spacer(1, 0.3*cm))

        cfop_alert_rows = []
        for alerta in cfops['alertas']:
            cfop_alert_rows.append([
                alerta.get('CFOP', ''),
                alerta.get('Tipo', ''),
                alerta.get('Mensagem', '')
            ])

        create_paginated_table(
            data_rows=cfop_alert_rows,
            columns=["<b>CFOP</b>", "<b>Tipo</b>", "<b>Mensagem</b>"],
            col_widths=[2.5*cm, 3.5*cm, 9.5*cm],
            title="",
            story=story,
            heading_style=heading_style,
            items_per_page=25
        )

    # ── CFOPs: TODOS standard ──
    if cfops.get('standard'):
        story.append(PageBreak())
        story.append(Paragraph(f"✅ CFOPs Standard - Operações Atendidas ({len(cfops['standard'])} CFOPs)", heading_style))
        story.append(Spacer(1, 0.2*cm))

        std_rows = [[cfop, "✅ Atendido (Standard)"] for cfop in sorted(cfops['standard'])]
        create_paginated_table(
            data_rows=std_rows,
            columns=["<b>CFOP</b>", "<b>Status</b>"],
            col_widths=[3*cm, 12.5*cm],
            title="",
            story=story,
            heading_style=heading_style,
            items_per_page=35
        )

    # ── Footer ──
    story.append(Spacer(1, 2*cm))
    footer_text = f"""
    <para alignment="center">
    <font size="8" color="grey">
    Relatório gerado automaticamente pelo IDT Analyzer<br/>
    Thomson Reuters | {datetime.now().strftime("%d/%m/%Y às %H:%M")}
    </font>
    </para>
    """
    story.append(Paragraph(footer_text, body_style))

    # Build PDF
    doc.build(story)

    buffer.seek(0)
    return buffer.read()


def get_status_text(score):
    """Return status text based on score"""
    if score is None:
        return "N/A"
    if score >= 90:
        return "✅ Excelente"
    if score >= 80:
        return "✓ Bom"
    if score >= 50:
        return "⚠ Atenção"
    return "❌ Crítico"


if __name__ == "__main__":
    print("PDF Generator module loaded")
    print("Use generate_pdf(result) to create a PDF report")
