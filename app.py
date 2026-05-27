"""
IDT Pre-Diagnóstico — Analisador de Aderência
Streamlit app with authentication, history, and PDF export
"""

import io
import json
import tempfile
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

from idt_engine import run_analysis
import db_manager
import pdf_generator

# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Thomson Reuters | IDT Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Thomson Reuters Theme ─────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Thomson Reuters Brand Colors */
  :root {
    --tr-green: #123015;
    --tr-orange: #D64000;
    --tr-light-gray: #F5F5F5;
    --tr-dark-gray: #333333;
  }

  /* Main App Background */
  .main {
    background-color: #FFFFFF;
  }

  /* Sidebar Styling */
  [data-testid="stSidebar"] {
    background-color: var(--tr-green);
  }

  [data-testid="stSidebar"] * {
    color: #FFFFFF !important;
  }

  /* Headers with Thomson Reuters Orange */
  h1 {
    color: var(--tr-orange) !important;
    font-weight: 600 !important;
    margin-bottom: 1rem !important;
  }

  h2 {
    color: var(--tr-orange) !important;
    font-weight: 600 !important;
    margin-top: 1.5rem !important;
    margin-bottom: 0.75rem !important;
  }

  h3 {
    color: var(--tr-green) !important;
    font-weight: 600 !important;
    margin-top: 1rem !important;
    margin-bottom: 0.5rem !important;
  }

  /* Buttons */
  .stButton > button {
    border-radius: 4px;
    font-weight: 500;
    transition: all 0.3s;
  }

  .stButton > button[kind="primary"] {
    background-color: var(--tr-orange);
    color: white;
    border-color: var(--tr-orange);
    font-weight: 600;
  }

  .stButton > button[kind="primary"]:hover {
    background-color: #B83800;
    color: white;
    border-color: #B83800;
  }

  /* Sidebar Buttons (Logout) */
  [data-testid="stSidebar"] button {
    background-color: var(--tr-orange) !important;
    color: white !important;
    border: none !important;
    font-weight: 600 !important;
  }

  [data-testid="stSidebar"] button:hover {
    background-color: #B83800 !important;
  }

  /* Metrics */
  [data-testid="stMetric"] {
    background: var(--tr-light-gray);
    border-left: 4px solid var(--tr-orange);
    padding: 16px;
    border-radius: 4px;
  }

  [data-testid="stMetricValue"] {
    color: var(--tr-green) !important;
    font-weight: 700 !important;
  }

  /* Score Colors */
  .score-green  { color: #2D7A3E; }
  .score-yellow { color: var(--tr-orange); }
  .score-red    { color: #D32F2F; }

  /* Tags */
  .gap-tag {
    display: inline-block;
    background: #FFF3E0;
    border: 1px solid var(--tr-orange);
    border-radius: 4px;
    font-size: 12px;
    padding: 4px 10px;
    margin: 2px;
    color: var(--tr-orange);
    font-weight: 500;
  }

  .out-tag {
    display: inline-block;
    background: #FFEBEE;
    border: 1px solid #D32F2F;
    border-radius: 4px;
    font-size: 12px;
    padding: 4px 10px;
    margin: 2px;
    color: #D32F2F;
    font-weight: 500;
  }

  .in-tag {
    display: inline-block;
    background: #E8F5E9;
    border: 1px solid #2D7A3E;
    border-radius: 4px;
    font-size: 12px;
    padding: 4px 10px;
    margin: 2px;
    color: #2D7A3E;
    font-weight: 500;
  }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
    gap: 8px;
  }

  .stTabs [data-baseweb="tab"] {
    background-color: var(--tr-light-gray);
    border-radius: 4px 4px 0 0;
    padding: 10px 20px;
    color: var(--tr-dark-gray);
  }

  .stTabs [aria-selected="true"] {
    background-color: var(--tr-orange);
    color: white !important;
  }

  /* Success/Error/Warning Messages */
  .stSuccess {
    background-color: #E8F5E9;
    border-left: 4px solid #2D7A3E;
  }

  .stError {
    background-color: #FFEBEE;
    border-left: 4px solid #D32F2F;
  }

  .stWarning {
    background-color: #FFF3E0;
    border-left: 4px solid var(--tr-orange);
  }

  /* DataFrames */
  .dataframe {
    border: 1px solid #E0E0E0;
  }

  .dataframe th {
    background-color: var(--tr-green) !important;
    color: white !important;
    font-weight: 600;
  }

  /* Expanders */
  .streamlit-expanderHeader {
    background-color: var(--tr-light-gray);
    border-radius: 4px;
    font-weight: 500;
  }

  /* Progress Bars */
  .stProgress > div > div {
    background-color: var(--tr-orange);
  }
</style>
""", unsafe_allow_html=True)


# ── Authentication ────────────────────────────────────────────────────────────

def load_auth_config():
    """Load authentication configuration"""
    config_path = Path("config_auth.yaml")
    if not config_path.exists():
        st.error("❌ Arquivo config_auth.yaml não encontrado!")
        st.info("Execute: python generate_password.py para gerar senhas")
        st.stop()

    with open(config_path) as file:
        config = yaml.load(file, Loader=SafeLoader)
    return config


def save_auth_config(config):
    """Save authentication configuration"""
    config_path = Path("config_auth.yaml")
    with open(config_path, 'w') as file:
        yaml.dump(config, file, default_flow_style=False, allow_unicode=True)


# Initialize authenticator
config = load_auth_config()

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Login
authenticator.login()

# Get authentication status from session state
authentication_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")
username = st.session_state.get("username")

if authentication_status == False:
    st.error('❌ Usuário ou senha incorretos')
    st.stop()

if authentication_status == None:
    st.warning('⚠️ Por favor, faça login para acessar o sistema')
    st.stop()

# ── User logged in ────────────────────────────────────────────────────────────

# Sidebar
with st.sidebar:
    # Thomson Reuters
    st.markdown("""
    <h2 style="color: white; text-align: center; margin-bottom: 1rem;">
        THOMSON REUTERS
    </h2>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.write(f'**Bem-vindo, {name}!**')
    authenticator.logout(button_name='Sair', location='sidebar')
    st.markdown("---")

    # Navigation
    st.markdown("### Navegação")
    page = st.radio(
        "Menu",
        ["▸ Nova Análise", "▸ Histórico", "▸ Configurações"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.caption(f"Usuário: **{username}**")
    st.caption(f"Perfil: **{config['credentials']['usernames'][username].get('role', 'user')}**")


# ── Page Header ───────────────────────────────────────────────────────────────
def render_page_header(title, subtitle=""):
    """Render Thomson Reuters style page header"""
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #123015 0%, #1a4520 100%);
        padding: 2rem;
        border-radius: 8px;
        margin-bottom: 2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    ">
        <h1 style="color: white !important; margin: 0; font-size: 2.5rem; font-weight: 600;">
            {title}
        </h1>
        {f'<p style="color: #FFFFFF; opacity: 0.9; margin: 0.5rem 0 0 0; font-size: 1.1rem;">{subtitle}</p>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def score_color(s):
    if s is None:
        return "score-yellow"
    if s >= 80:
        return "score-green"
    if s >= 50:
        return "score-yellow"
    return "score-red"


def score_label(s):
    if s is None:
        return "—"
    return f"{s}%"


def render_metric(label, value, color_class="score-green"):
    st.markdown(f"""
    <div class="metric-box">
      <div class="label">{label}</div>
      <div class="value {color_class}">{value}</div>
    </div>
    """, unsafe_allow_html=True)


def render_uf_table(uf_summary: dict, direction: str):
    if not uf_summary:
        st.info("Nenhum par NCM×UF analisado.")
        return

    rows = []
    for uf, v in sorted(uf_summary.items()):
        semaforo = "🟢" if v["score"] == 100 else ("🟡" if v["score"] >= 50 else "🔴")
        rows.append({
            "UF": uf,
            "Score (%)": v["score"],
            "NCMs cobertos": v["covered"],
            "NCMs com gap": v["gap"],
            "Total NCMs": v["total"],
            " ": semaforo,
        })
    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Score (%)": st.column_config.ProgressColumn(
                "Cobertura (%)", min_value=0, max_value=100, format="%.1f%%"
            ),
        },
        hide_index=True,
    )


def render_gap_detail(gaps: list, label: str):
    if not gaps:
        st.success(f"Nenhum gap encontrado em {label}.")
        return
    df = pd.DataFrame(gaps)[["NCM", "UF", "Descricao", "Cobertura"]]
    df.columns = ["NCM", "UF", "Descrição", "Cobertura (%)"]
    st.dataframe(df, use_container_width=True, hide_index=True)


def build_excel_report(result: dict) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:

        # ── Resumo ──
        g = result["general"]
        summary_rows = [
            ["Score Geral", result["overall_score"]],
            ["Segmento", g.get("segmento", "")],
            ["Estados", g.get("estados", "")],
            ["Atividade", g.get("atividade", "")],
            ["Escopo", g.get("escopo", "")],
            ["Volume Saída / ano", g.get("vol_saida", "")],
            ["Volume Entrada / ano", g.get("vol_entrada", "")],
            ["Setor Inbound (aderência)", result["sector"]["inbound"]],
            ["Setor Outbound (aderência)", result["sector"]["outbound"]],
            ["Score NCM Compras (%)", result["ncm_compras"].get("score")],
            ["Score NCM Vendas (%)", result["ncm_vendas"].get("score")],
            ["Score Municípios (%)", result["municipios"].get("score")],
            ["Score CFOPs (%)", result.get("cfops", {}).get("score")],
            ["Total de Linhas (Municípios)", result["municipios"].get("total_linhas", 0)],
            ["Linhas Atendidas", result["municipios"].get("linhas_atendidas", 0)],
            ["Linhas Não Atendidas", result["municipios"].get("linhas_nao_atendidas", 0)],
            ["Linhas Inválidas (UF inválida)", result["municipios"].get("linhas_invalidas", 0)],
            ["Municípios Únicos Cobertos (IDT)", len(result["municipios"].get("in_scope", []))],
            ["Municípios Únicos Não Cobertos", len(result["municipios"].get("out_of_scope", []))],
            ["Municípios Únicos Inválidos", len(result["municipios"].get("invalid", []))],
            ["CFOPs não-standard (alertas)", len(result.get("cfops", {}).get("alertas", []))],
        ]
        pd.DataFrame(summary_rows, columns=["Dimensão", "Valor"]).to_excel(
            writer, sheet_name="Resumo Executivo", index=False)

        # ── NCM Compras por UF ──
        uf_c = result["ncm_compras"].get("uf_summary", {})
        if uf_c:
            rows = [{"UF": uf, "Score (%)": v["score"], "Cobertos": v["covered"],
                     "Gap": v["gap"], "Total": v["total"]}
                    for uf, v in sorted(uf_c.items())]
            pd.DataFrame(rows).to_excel(writer, sheet_name="NCM Compras por UF", index=False)

        # ── NCM Vendas por UF ──
        uf_v = result["ncm_vendas"].get("uf_summary", {})
        if uf_v:
            rows = [{"UF": uf, "Score (%)": v["score"], "Cobertos": v["covered"],
                     "Gap": v["gap"], "Total": v["total"]}
                    for uf, v in sorted(uf_v.items())]
            pd.DataFrame(rows).to_excel(writer, sheet_name="NCM Vendas por UF", index=False)

        # ── Gaps Compras ──
        gaps_c = result["ncm_compras"].get("gaps", [])
        if gaps_c:
            pd.DataFrame(gaps_c)[["NCM", "UF", "Descricao", "Cobertura"]].to_excel(
                writer, sheet_name="Gaps NCM Compras", index=False)

        # ── Gaps Vendas ──
        gaps_v = result["ncm_vendas"].get("gaps", [])
        if gaps_v:
            pd.DataFrame(gaps_v)[["NCM", "UF", "Descricao", "Cobertura"]].to_excel(
                writer, sheet_name="Gaps NCM Vendas", index=False)

        # ── Municípios ──
        m = result["municipios"]
        detail = m.get("detail", [])
        if detail:
            mun_rows = [
                {
                    "Município": r.get("Cidade", ""),
                    "UF": r.get("UF", ""),
                    "Status": r.get("Status", ""),
                    "Modo de Match": r.get("Modo_Match") or "-",
                    "Similaridade": r.get("Similaridade") if r.get("Similaridade") is not None else "-",
                }
                for r in detail
            ]
            pd.DataFrame(mun_rows).to_excel(writer, sheet_name="Municípios", index=False)
        else:
            # Fallback para formato legado
            mun_rows = (
                [{"Município": c, "Status": "Atendido"} for c in m.get("in_scope", [])] +
                [{"Município": c, "Status": "Não Atendido"} for c in m.get("out_of_scope", [])]
            )
            if mun_rows:
                pd.DataFrame(mun_rows).to_excel(writer, sheet_name="Municípios", index=False)

        # ── CFOPs ──
        cfop = result.get("cfops", {})
        if cfop.get("alertas"):
            cfop_rows = []
            for alerta in cfop["alertas"]:
                cfop_rows.append({
                    "CFOP": alerta["CFOP"],
                    "Tipo": alerta["Tipo"],
                    "Mensagem": alerta["Mensagem"]
                })
            pd.DataFrame(cfop_rows).to_excel(writer, sheet_name="Alertas CFOPs", index=False)

        # Lista completa de CFOPs
        all_cfops = []
        for cfop_code in cfop.get("standard", []):
            all_cfops.append({"CFOP": cfop_code, "Status": "Standard (Atendido)"})
        for cfop_code in cfop.get("non_standard", []):
            all_cfops.append({"CFOP": cfop_code, "Status": "Não-Standard (Customização)"})
        if all_cfops:
            pd.DataFrame(all_cfops).to_excel(writer, sheet_name="CFOPs Declarados", index=False)

    buf.seek(0)
    return buf.read()


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: Nova Análise
# ═════════════════════════════════════════════════════════════════════════════

if page == "▸ Nova Análise":
    render_page_header(
        "IDT Analyzer",
        "Analisador de Aderência · Onesource Determination"
    )

    # Verificar se base de aderência está configurada
    ADHERENCE_PATH = Path("config/Aderencia.xlsm")

    if not ADHERENCE_PATH.exists():
        st.error("❌ Base de Aderência não configurada!")
        st.info("Por favor, solicite ao administrador para configurar a base de aderência em **Configurações**.")
        st.stop()

    st.markdown("---")

    st.markdown("### 📝 Dados do Cliente")

    cliente_nome = st.text_input(
        "Nome do Cliente",
        placeholder="Digite o nome do cliente ou empresa...",
        help="Este nome será usado para identificar a análise no histórico"
    )

    st.markdown("### 📂 Arquivo do Pré-Diagnóstico")
    st.write("Faça upload do arquivo Excel preenchido pelo cliente")

    file_diag = st.file_uploader(
        "arquivo",
        type=["xlsx", "xlsm"],
        key="diag",
        label_visibility="collapsed"
    )

    if file_diag:
        st.info(f"📄 Arquivo selecionado: **{file_diag.name}**")

    st.markdown("---")

    run_btn = st.button("🔍 ANALISAR ADERÊNCIA", type="primary",
                        disabled=(file_diag is None or not cliente_nome.strip()),
                        use_container_width=True)

    if file_diag and not cliente_nome.strip():
        st.warning("⚠️ Por favor, preencha o nome do cliente antes de analisar.")

    if run_btn and file_diag:
        with st.spinner("Processando…"):
            with tempfile.TemporaryDirectory() as tmp:
                p_diag = Path(tmp) / file_diag.name
                p_diag.write_bytes(file_diag.read())

                try:
                    # Usa aderência configurada
                    result = run_analysis(str(p_diag), str(ADHERENCE_PATH))

                    # Save to database with custom client name
                    analysis_id = db_manager.save_analysis(
                        usuario=username,
                        result=result,
                        arquivo_prediag=file_diag.name,
                        arquivo_aderencia="Aderencia.xlsm (Sistema)",
                        cliente_nome_custom=cliente_nome.strip()
                    )
                    st.session_state['last_result'] = result
                    st.session_state['last_analysis_id'] = analysis_id
                    st.session_state['last_cliente_nome'] = cliente_nome.strip()

                except Exception as e:
                    import traceback
                    st.error(f"Erro na análise: {e}")
                    st.error("**Traceback completo:**")
                    st.code(traceback.format_exc())
                    st.stop()

        st.success(f"✅ Análise concluída! (ID: #{st.session_state['last_analysis_id']})")

        result = st.session_state['last_result']

        g = result["general"]
        st.markdown("---")

        # ── Header ────────────────────────────────────────────────────────────────
        st.markdown(f"### {g.get('segmento','?')} · {g.get('atividade','?')} · {g.get('estados','?')}")
        st.caption(
            f"Escopo: **{g.get('escopo','?')}** | "
            f"Setor base: **{result['sector']['inbound']}** (in) / **{result['sector']['outbound']}** (out) | "
            f"Volume entrada: **{g.get('vol_entrada','?')} NF/ano** | "
            f"Volume saída: **{g.get('vol_saida','?')} NF/ano**"
        )

        # ── Score cards ───────────────────────────────────────────────────────────
        st.markdown("### 📊 Scores de Aderência")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ov = result["overall_score"]
            st.metric("Score Geral", score_label(ov), help="Média ponderada: NCM Compras (35%), NCM Vendas (35%), Municípios únicos (30%)")
        with c2:
            sc = result["ncm_compras"].get("score")
            st.metric("NCM Compras", score_label(sc))
        with c3:
            sv = result["ncm_vendas"].get("score")
            st.metric("NCM Vendas", score_label(sv))
        with c4:
            sm = result["municipios"].get("score")
            st.metric("Municípios ISS", score_label(sm))

        st.markdown("---")

        # ── NCM Tabs ──────────────────────────────────────────────────────────────
        tab_compras, tab_vendas, tab_mun, tab_cfop, tab_cst = st.tabs([
            "📥 NCM Compras", "📤 NCM Vendas", "🏙 Municípios ISS", "⚠️ CFOPs", "📋 CSTs"
        ])

        with tab_compras:
            nc = result["ncm_compras"]
            if nc["total_pairs"] == 0:
                st.info("Nenhum NCM de Compras preenchido no pré-diagnóstico (UF Fornecedor × NCM).")
            else:
                st.markdown(f"""
                **{nc['total_pairs']}** pares NCM × UF analisados ·
                **{nc['covered']}** cobertos ·
                **{len(nc['gaps'])}** com gap
                """)
                st.markdown("##### Cobertura por UF do Fornecedor")
                render_uf_table(nc.get("uf_summary", {}), "Compras")
                if nc["gaps"]:
                    with st.expander(f"📋 Ver {len(nc['gaps'])} gaps em detalhe"):
                        render_gap_detail(nc["gaps"], "Compras")

        with tab_vendas:
            nv = result["ncm_vendas"]
            if nv["total_pairs"] == 0:
                st.info("Nenhum NCM de Vendas preenchido no pré-diagnóstico (UF Cliente × NCM).")
            else:
                st.markdown(f"""
                **{nv['total_pairs']}** pares NCM × UF analisados ·
                **{nv['covered']}** cobertos ·
                **{len(nv['gaps'])}** com gap
                """)
                st.markdown("##### Cobertura por UF do Cliente / Destino")
                render_uf_table(nv.get("uf_summary", {}), "Vendas")
                if nv["gaps"]:
                    with st.expander(f"📋 Ver {len(nv['gaps'])} gaps em detalhe"):
                        render_gap_detail(nv["gaps"], "Vendas")

        with tab_mun:
            m = result["municipios"]

            # ── SCORE PRINCIPAL ──
            if m.get("score") is not None:
                st.markdown(f"### Score: {m['score']:.2f}% (baseado em volumetria de linhas)")

            # ── MÉTRICAS POR VOLUMETRIA (LINHAS) ──
            st.markdown("#### 📊 Volumetria (Linhas)")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📋 Total de Linhas", m.get("total_linhas", 0))
            with col2:
                st.metric("✅ Atendidas", m.get("linhas_atendidas", 0))
            with col3:
                st.metric("❌ Não Atendidas", m.get("linhas_nao_atendidas", 0))
            with col4:
                st.metric("⚠️ Inválidas", m.get("linhas_invalidas", 0),
                          help="Municípios com UF inválida (ex: 'NI')")

            # ── MÉTRICAS POR MUNICÍPIOS ÚNICOS ──
            st.markdown("#### 🏙️ Municípios Únicos")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Únicos", m.get("total", 0))
            with col2:
                st.metric("Atendidos", m.get("covered", 0))
            with col3:
                st.metric("Não Atendidos", m.get("not_covered", 0))
            with col4:
                st.metric("Inválidos", m.get("invalid_count", 0))

            detail = m.get("detail", [])
            total_unicos = m.get("total", 0)
            total_linhas = m.get("total_linhas", 0)
            invalid_count = m.get("invalid_count", 0)
            linhas_inv = m.get("linhas_invalidas", 0)

            # Aviso se houver municípios inválidos
            if invalid_count > 0:
                pct = round((linhas_inv / total_linhas * 100), 1) if total_linhas else 0
                st.warning(
                    f"⚠️ **{linhas_inv} linhas ({pct}%)** possuem UF inválida ou não informada. "
                    f"Recomenda-se revisar o arquivo Excel para corrigir estas UFs."
                )

            st.info(
                f"ℹ️ Análise de **{total_linhas}** linhas do pré-diagnóstico "
                f"(**{total_unicos}** municípios únicos). "
                f"Score = (Linhas Atendidas / Total de Linhas) × 100"
            )

            if detail:
                # Monta DataFrame estilo NCM
                rows = []
                for r in detail:
                    rows.append({
                        "Município": r.get("Cidade", ""),
                        "UF": r.get("UF", ""),
                        "Status": r.get("Status", ""),
                        "Modo de Match": r.get("Modo_Match") or "-",
                        "Similaridade": r.get("Similaridade") if r.get("Similaridade") is not None else "-",
                    })
                df_mun = pd.DataFrame(rows)

                # Filtros interativos
                st.markdown("---")
                f1, f2 = st.columns([3, 2])
                with f1:
                    filtro_status = st.multiselect(
                        "Filtrar por status",
                        options=["Atendido", "Não Atendido", "Município Não Válido"],
                        default=["Atendido", "Não Atendido", "Município Não Válido"],
                        key="mun_filtro_status",
                    )
                with f2:
                    ufs_disponiveis = sorted(df_mun["UF"].unique().tolist())
                    filtro_uf = st.multiselect(
                        "Filtrar por UF",
                        options=ufs_disponiveis,
                        default=ufs_disponiveis,
                        key="mun_filtro_uf",
                    )

                df_filtrado = df_mun[
                    df_mun["Status"].isin(filtro_status) &
                    df_mun["UF"].isin(filtro_uf)
                ]

                st.markdown(f"**Exibindo {len(df_filtrado)} de {len(df_mun)} linhas**")
                st.dataframe(
                    df_filtrado,
                    use_container_width=True,
                    hide_index=True,
                    height=min(600, 40 + 35 * min(len(df_filtrado), 15)),
                )

                # Avisos sobre matches via fuzzy (similaridade < 1.0)
                fuzzy = m.get("fuzzy_matches", [])
                if fuzzy:
                    with st.expander(f"🔍 Matches por similaridade ({len(fuzzy)})"):
                        st.caption("Estas cidades casaram com a base via aproximação (acentuação/typos). Revise se o match está correto.")
                        df_fuzzy = pd.DataFrame(fuzzy)
                        st.dataframe(df_fuzzy, use_container_width=True, hide_index=True)
            else:
                st.warning("⚠️ Nenhum município do pré-diagnóstico foi extraído ou todos foram filtrados como inválidos.")
                diag = m.get("diagnostico", {})
                if diag:
                    with st.expander("📊 Diagnóstico — onde os municípios foram perdidos"):
                        st.json(diag)

        with tab_cfop:
            cfop = result.get("cfops", {})
            c_std, c_nstd = st.columns(2)
            with c_std:
                st.metric("CFOPs Standard", len(cfop.get("standard", [])))
            with c_nstd:
                alertas_count = len(cfop.get("alertas", []))
                st.metric("CFOPs Não-Standard", len(cfop.get("non_standard", [])),
                          delta=f"{alertas_count} alertas" if alertas_count > 0 else None,
                          delta_color="inverse" if alertas_count > 0 else "off")

            # Verifica se há CFOPs declarados
            if cfop.get("total_cfops", 0) == 0:
                st.info("ℹ️ Não há dados de CFOP para analisar")
            elif cfop.get("alertas"):
                st.markdown("### ⚠️ Alertas de Operações Não-Standard")
                st.warning(f"**{len(cfop['alertas'])} CFOPs requerem customização** — operações não atendidas pelo IDT standard")

                alerta_rows = []
                for alerta in cfop["alertas"]:
                    alerta_rows.append({
                        "CFOP": alerta["CFOP"],
                        "Tipo": alerta["Tipo"],
                        "Mensagem": alerta["Mensagem"]
                    })
                st.dataframe(pd.DataFrame(alerta_rows), use_container_width=True, hide_index=True)
            else:
                st.success("✅ Todos os CFOPs declarados são operações standard atendidas pelo IDT")

            if cfop.get("standard"):
                with st.expander(f"Ver {len(cfop['standard'])} CFOPs standard"):
                    html_tags = " ".join(
                        f'<span class="in-tag">{c}</span>' for c in cfop["standard"])
                    st.markdown(html_tags, unsafe_allow_html=True)

        with tab_cst:
            cst = result.get("cst_coverage", {})
            for tributo, csts in cst.items():
                with st.expander(f"**{tributo}** — {sum(csts.values())}/{len(csts)} CSTs atendidos"):
                    rows = [{"CST": k, "Atendido": "✅ Sim" if v else "❌ Não"}
                            for k, v in csts.items()]
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("---")

        # ── Download ──────────────────────────────────────────────────────────────
        st.markdown("### 📥 Exportar Resultados")
        col_xl, col_pdf = st.columns(2)

        with col_xl:
            xlsx_bytes = build_excel_report(result)
            st.download_button(
                "⬇ Baixar Relatório Excel",
                data=xlsx_bytes,
                file_name=f"aderencia_IDT_{g.get('segmento','cliente').replace(' ','_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        with col_pdf:
            with st.spinner("Gerando PDF..."):
                # Passa nome do cliente para o PDF
                nome_cliente = st.session_state.get('last_cliente_nome')
                pdf_bytes = pdf_generator.generate_pdf(result, cliente_nome=nome_cliente)
            st.download_button(
                "📄 Baixar Relatório PDF Executivo",
                data=pdf_bytes,
                file_name=f"aderencia_IDT_{g.get('segmento','cliente').replace(' ','_')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: Histórico
# ═════════════════════════════════════════════════════════════════════════════

elif page == "▸ Histórico":
    render_page_header("Histórico de Análises", "Consulte e gerencie análises anteriores")

    # Verifica se é admin
    user_role = config['credentials']['usernames'][username].get('role', 'user')
    is_admin = user_role == 'admin'

    # Admin pode visualizar histórico de todos os usuários
    if is_admin:
        st.markdown("### 👑 Modo Administrador")

        view_mode = st.radio(
            "Visualizar histórico de:",
            ["Todos os usuários", "Usuário específico", "Apenas meu histórico"],
            horizontal=True
        )

        if view_mode == "Usuário específico":
            # Lista de usuários para filtrar
            all_users = list(config['credentials']['usernames'].keys())
            selected_user = st.selectbox("Selecione o usuário:", all_users)
            filter_user = selected_user
        elif view_mode == "Apenas meu histórico":
            filter_user = username
        else:  # Todos os usuários
            filter_user = None

        st.markdown("---")
    else:
        filter_user = username

    # Stats
    if filter_user:
        stats = db_manager.get_stats_by_user(filter_user)
        stats_title = f"Estatísticas de {filter_user}" if is_admin and filter_user != username else "Suas Estatísticas"
    else:
        # Stats de todos os usuários (admin)
        stats = db_manager.get_stats_by_user(None)  # Passa None para pegar de todos
        stats_title = "Estatísticas Gerais (Todos os Usuários)"

    if stats.get("total_analyses", 0) == 0:
        msg = "Nenhuma análise encontrada." if is_admin and not filter_user else "Você ainda não realizou nenhuma análise."
        st.info(msg)
    else:
        st.markdown(f"### {stats_title}")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Total de Análises", stats["total_analyses"])
        with c2:
            st.metric("Score Médio", f"{stats['avg_score']:.1f}%" if stats['avg_score'] else "N/A")

        st.markdown("---")
        st.markdown("### Histórico Recente")

        # Filtro por nome do cliente
        filter_cliente = st.text_input(
            "🔍 Filtrar por nome do cliente",
            placeholder="Digite parte do nome para filtrar...",
            help="Filtra a lista de análises pelo nome do cliente"
        )

        # Load history
        if filter_user:
            history_df = db_manager.get_user_history(filter_user, limit=50)
        else:
            # Admin vendo todos os usuários
            history_df = db_manager.get_all_history(limit=100)

        if not history_df.empty:
            # Aplicar filtro por nome do cliente se houver
            if filter_cliente.strip():
                history_df = history_df[
                    history_df['cliente_nome'].str.contains(filter_cliente.strip(), case=False, na=False)
                ]

            if history_df.empty:
                st.info(f"Nenhuma análise encontrada com o nome '{filter_cliente}'")
            else:
                # Format display
                display_df = history_df.copy()
                display_df["timestamp"] = display_df["timestamp"].dt.strftime("%d/%m/%Y %H:%M")

                # Define colunas a renomear
                rename_cols = {
                    "id": "ID",
                    "timestamp": "Data/Hora",
                    "cliente_nome": "Cliente",
                    "cliente_segmento": "Segmento",
                    "score_geral": "Score Geral (%)",
                    "gaps_compras": "Gaps Compras",
                    "gaps_vendas": "Gaps Vendas",
                    "cfops_nao_standard": "Alertas CFOP"
                }

                # Se admin vendo todos, adiciona coluna de usuário
                if is_admin and not filter_user and "usuario" in display_df.columns:
                    rename_cols["usuario"] = "Usuário"

                display_df = display_df.rename(columns=rename_cols)

                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Score Geral (%)": st.column_config.ProgressColumn(
                            "Score Geral (%)",
                            min_value=0,
                            max_value=100,
                            format="%.1f%%"
                        ),
                    }
                )

                # Load specific analysis
                st.markdown("---")
                st.markdown("### 🔍 Visualizar Análise")

                selected_id = st.selectbox(
                    "Selecione uma análise pelo ID:",
                    options=history_df["id"].tolist(),
                    format_func=lambda x: f"#{x} - {history_df[history_df['id']==x]['cliente_nome'].values[0]} ({history_df[history_df['id']==x]['timestamp'].values[0]})"
                )

                col_load, col_delete = st.columns([3, 1])

                with col_load:
                    if st.button("📂 Visualizar Detalhes", type="primary", use_container_width=True):
                        loaded_result = db_manager.get_analysis_by_id(selected_id)
                        if loaded_result:
                            st.session_state['viewing_result'] = loaded_result
                            st.session_state['viewing_id'] = selected_id
                            st.rerun()
                        else:
                            st.error("Análise não encontrada.")

                # Admin pode excluir análises individuais
                if is_admin:
                    with col_delete:
                        if st.button("🗑️ Excluir", type="secondary", use_container_width=True):
                            if db_manager.delete_analysis_by_id(selected_id):
                                st.session_state.delete_success = f"Análise #{selected_id} excluída com sucesso!"
                                # Limpar visualização se estava vendo essa análise
                                if 'viewing_id' in st.session_state and st.session_state['viewing_id'] == selected_id:
                                    del st.session_state['viewing_result']
                                    del st.session_state['viewing_id']
                                st.rerun()
                            else:
                                st.error("Erro ao excluir análise.")

                # Mostrar resultados se uma análise foi carregada
                if 'viewing_result' in st.session_state and 'viewing_id' in st.session_state:
                    result = st.session_state['viewing_result']
                    viewing_id = st.session_state['viewing_id']

                    st.markdown("---")
                    st.markdown(f"### 📊 Resultados da Análise #{viewing_id}")

                    if st.button("✖ Fechar Visualização"):
                        del st.session_state['viewing_result']
                        del st.session_state['viewing_id']
                        st.rerun()

                    g = result["general"]

                    # Header
                    st.markdown(f"**{g.get('segmento','?')}** · {g.get('atividade','?')} · {g.get('estados','?')}")
                    st.caption(
                        f"Escopo: **{g.get('escopo','?')}** | "
                        f"Volume entrada: **{g.get('vol_entrada','?')} NF/ano** | "
                        f"Volume saída: **{g.get('vol_saida','?')} NF/ano**"
                    )

                    # Score cards
                    st.markdown("### 📊 Scores de Aderência")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        ov = result["overall_score"]
                        st.metric("Score Geral", score_label(ov), help="Média ponderada das 3 dimensões")
                    with c2:
                        sc = result["ncm_compras"].get("score")
                        st.metric("NCM Compras", score_label(sc))
                    with c3:
                        sv = result["ncm_vendas"].get("score")
                        st.metric("NCM Vendas", score_label(sv))
                    with c4:
                        sm = result["municipios"].get("score")
                        st.metric("Municípios ISS", score_label(sm))

                    # Download buttons
                    st.markdown("---")
                    st.markdown("### 📥 Exportar Resultados")
                    col_xl, col_pdf = st.columns(2)

                    with col_xl:
                        xlsx_bytes = build_excel_report(result)
                        st.download_button(
                            "⬇ Baixar Excel",
                            data=xlsx_bytes,
                            file_name=f"analise_{viewing_id}_{g.get('segmento','cliente').replace(' ','_')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )

                    with col_pdf:
                        with st.spinner("Gerando PDF..."):
                            # Pega nome do cliente do result (salvo do banco de dados)
                            nome_cliente = result.get('_cliente_nome')
                            pdf_bytes = pdf_generator.generate_pdf(result, cliente_nome=nome_cliente)
                        st.download_button(
                            "📄 Baixar PDF",
                            data=pdf_bytes,
                            file_name=f"analise_{viewing_id}_{g.get('segmento','cliente').replace(' ','_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )

                    # Detalhes em expander
                    with st.expander("📋 Ver detalhes completos da análise", expanded=False):
                        tab_compras, tab_vendas, tab_mun, tab_cfop = st.tabs([
                            "📥 NCM Compras", "📤 NCM Vendas", "🏙 Municípios", "⚠️ CFOPs"
                        ])

                        with tab_compras:
                            nc = result["ncm_compras"]
                            if nc["total_pairs"] == 0:
                                st.info("Nenhum NCM de Compras preenchido.")
                            else:
                                st.markdown(f"**{nc['total_pairs']}** pares · **{nc['covered']}** cobertos · **{len(nc['gaps'])}** gaps")
                                if nc.get("uf_summary"):
                                    render_uf_table(nc.get("uf_summary", {}), "Compras")

                        with tab_vendas:
                            nv = result["ncm_vendas"]
                            if nv["total_pairs"] == 0:
                                st.info("Nenhum NCM de Vendas preenchido.")
                            else:
                                st.markdown(f"**{nv['total_pairs']}** pares · **{nv['covered']}** cobertos · **{len(nv['gaps'])}** gaps")
                                if nv.get("uf_summary"):
                                    render_uf_table(nv.get("uf_summary", {}), "Vendas")

                        with tab_mun:
                            m = result["municipios"]
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("✅ Cobertos", len(m.get("in_scope", [])))
                            with col2:
                                st.metric("⚠️ Não Cobertos", len(m.get("out_of_scope", [])))

                        with tab_cfop:
                            cfop = result.get("cfops", {})
                            if cfop.get("total_cfops", 0) == 0:
                                st.info("Não há dados de CFOP")
                            else:
                                st.metric("CFOPs Standard", len(cfop.get("standard", [])))
                                if cfop.get("alertas"):
                                    st.warning(f"**{len(cfop['alertas'])} CFOPs** requerem customização")

            # Admin pode excluir histórico em massa
            if is_admin:
                st.markdown("---")
                st.markdown("### 🗑️ Gerenciar Histórico (Admin)")

                with st.expander("⚠️ Exclusão em Massa", expanded=False):
                    st.warning("**Atenção:** Esta ação não pode ser desfeita!")

                    delete_mode = st.radio(
                        "O que deseja excluir?",
                        ["Todas as análises do sistema", "Análises de um usuário específico"],
                        key="delete_mode"
                    )

                    if delete_mode == "Análises de um usuário específico":
                        all_users = list(config['credentials']['usernames'].keys())
                        user_to_delete = st.selectbox(
                            "Selecione o usuário:",
                            all_users,
                            key="user_to_delete"
                        )
                        confirm_text = f"Confirmo que quero excluir TODAS as análises do usuário '{user_to_delete}'"
                    else:
                        user_to_delete = None
                        confirm_text = "Confirmo que quero excluir TODAS as análises do sistema"

                    confirm = st.checkbox(confirm_text)

                    if confirm:
                        if st.button("🗑️ Confirmar Exclusão", type="secondary"):
                            deleted_count = db_manager.delete_all_analyses(user_to_delete)
                            if user_to_delete:
                                st.session_state.delete_success = f"{deleted_count} análise(s) do usuário '{user_to_delete}' excluída(s) com sucesso!"
                            else:
                                st.session_state.delete_success = f"{deleted_count} análise(s) excluída(s) do sistema!"
                            st.rerun()

        # Mostrar mensagem de sucesso na exclusão
        if 'delete_success' in st.session_state:
            st.success(f"✅ {st.session_state.delete_success}", icon="✅")
            del st.session_state.delete_success


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: Configurações
# ═════════════════════════════════════════════════════════════════════════════

elif page == "▸ Configurações":
    render_page_header("Configurações", "Gerenciar conta, usuários e sistema")

    st.markdown("### Informações da Conta")
    st.write(f"**Nome:** {name}")
    st.write(f"**Usuário:** {username}")
    st.write(f"**Email:** {config['credentials']['usernames'][username].get('email', 'N/A')}")
    st.write(f"**Perfil:** {config['credentials']['usernames'][username].get('role', 'user')}")

    st.markdown("---")

    # ── Gerenciar Base de Aderência (ADMIN ONLY) ──
    user_role = config['credentials']['usernames'][username].get('role', 'user')

    if user_role == 'admin':
        st.markdown("### 🔧 Gerenciar Base de Aderência")
        st.caption("Apenas administradores podem gerenciar a base de aderência do sistema")

        ADHERENCE_PATH = Path("config/Aderencia.xlsm")

        # Mostrar status atual
        if ADHERENCE_PATH.exists():
            st.success("✅ Base de aderência configurada")
            file_stat = ADHERENCE_PATH.stat()
            st.info(f"""
            **Arquivo atual:**
            - Nome: `{ADHERENCE_PATH.name}`
            - Tamanho: {file_stat.st_size / 1024:.1f} KB
            - Última modificação: {datetime.fromtimestamp(file_stat.st_mtime).strftime('%d/%m/%Y %H:%M')}
            """)

            # Opção de substituir
            with st.expander("🔄 Substituir Base de Aderência"):
                st.warning("⚠️ Substituir a base de aderência afetará todas as futuras análises!")

                new_ader = st.file_uploader(
                    "Novo arquivo de aderência",
                    type=["xlsx", "xlsm"],
                    key="new_ader"
                )

                if new_ader:
                    if st.button("💾 Confirmar Substituição", type="primary"):
                        try:
                            # Criar backup antes
                            backup_path = ADHERENCE_PATH.parent / f"Aderencia_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsm"
                            ADHERENCE_PATH.rename(backup_path)
                            st.info(f"Backup criado: {backup_path.name}")

                            # Salvar nova aderência
                            ADHERENCE_PATH.write_bytes(new_ader.read())
                            st.success("✅ Base de aderência atualizada com sucesso!", icon="✅")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao atualizar: {e}")
        else:
            st.warning("⚠️ Base de aderência NÃO configurada")
            st.info("Faça upload da base de aderência para habilitar análises no sistema.")

            # Upload inicial
            initial_ader = st.file_uploader(
                "Arquivo de Aderência (.xlsx ou .xlsm)",
                type=["xlsx", "xlsm"],
                key="initial_ader"
            )

            if initial_ader:
                if st.button("💾 Salvar Base de Aderência", type="primary"):
                    try:
                        # Criar diretório se não existir
                        ADHERENCE_PATH.parent.mkdir(parents=True, exist_ok=True)

                        # Salvar arquivo
                        ADHERENCE_PATH.write_bytes(initial_ader.read())
                        st.success("✅ Base de aderência configurada com sucesso!", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar: {e}")

        st.markdown("---")

        # ── Gerenciar Usuários (ADMIN ONLY) ──
        st.markdown("### 👥 Gerenciar Usuários")
        st.caption("Cadastrar e gerenciar usuários do sistema")

        tab_add, tab_manage = st.tabs(["➕ Cadastrar Novo", "📋 Gerenciar Existentes"])

        with tab_add:
            st.markdown("#### Cadastrar Novo Usuário")

            # Mostrar mensagem de sucesso se houver
            if 'user_create_success' in st.session_state:
                st.success(f"✅ {st.session_state.user_create_success}", icon="✅")
                del st.session_state.user_create_success

            with st.form("add_user_form"):
                new_username = st.text_input("Usuário (login)", placeholder="usuario.nome")
                new_name = st.text_input("Nome Completo", placeholder="Nome Sobrenome")
                new_email = st.text_input("Email", placeholder="usuario@exemplo.com")
                new_password = st.text_input("Senha", type="password", placeholder="Senha temporária")
                new_role = st.selectbox("Perfil", ["user", "admin"])

                submit_new = st.form_submit_button("➕ Cadastrar Usuário", type="primary")

                if submit_new:
                    if not new_username or not new_name or not new_password:
                        st.error("❌ Preencha todos os campos obrigatórios!")
                    elif new_username in config['credentials']['usernames']:
                        st.error(f"❌ Usuário '{new_username}' já existe!")
                    else:
                        try:
                            # Hash da senha
                            import streamlit_authenticator as stauth
                            hashed_pw = stauth.Hasher([new_password]).generate()[0]

                            # Adiciona novo usuário
                            config['credentials']['usernames'][new_username] = {
                                'email': new_email,
                                'name': new_name,
                                'password': hashed_pw,
                                'role': new_role
                            }

                            # Salva configuração
                            save_auth_config(config)

                            # Armazena mensagem de sucesso para mostrar após rerun
                            st.session_state.user_create_success = f"Usuário '{new_username}' cadastrado com sucesso!\n\n**Credenciais:**\n- Usuário: `{new_username}`\n- Senha: `{new_password}`\n- Perfil: {new_role}"
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao cadastrar usuário: {e}")

        with tab_manage:
            st.markdown("#### Usuários Cadastrados")
            st.caption(f"Total de usuários: {len(config['credentials']['usernames'])}")

            # Mostrar mensagem de sucesso se houver
            if 'user_update_success' in st.session_state:
                st.success(f"✅ {st.session_state.user_update_success}", icon="✅")
                del st.session_state.user_update_success

            if 'user_delete_success' in st.session_state:
                st.success(f"✅ {st.session_state.user_delete_success}", icon="✅")
                del st.session_state.user_delete_success

            # Lista cada usuário com expander
            for uname in sorted(config['credentials']['usernames'].keys()):
                user_data = config['credentials']['usernames'][uname]
                role_emoji = "👑" if user_data.get('role', 'user') == 'admin' else "👤"

                with st.expander(f"{role_emoji} **{uname}** — {user_data.get('name', 'N/A')}"):
                    # Informações do usuário
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.write(f"**Usuário:** `{uname}`")
                        st.write(f"**Nome:** {user_data.get('name', 'N/A')}")
                    with col_info2:
                        st.write(f"**Email:** {user_data.get('email', 'N/A')}")
                        st.write(f"**Perfil:** {user_data.get('role', 'user')}")

                    st.markdown("---")

                    # Formulário de edição
                    with st.form(f"edit_user_{uname}"):
                        st.markdown("**Editar Dados**")

                        edit_name = st.text_input("Nome Completo", value=user_data.get('name', ''), key=f"name_{uname}")
                        edit_email = st.text_input("Email", value=user_data.get('email', ''), key=f"email_{uname}")

                        col_role, col_pwd = st.columns(2)
                        with col_role:
                            edit_role = st.selectbox(
                                "Perfil",
                                options=["user", "admin"],
                                index=0 if user_data.get('role', 'user') == 'user' else 1,
                                key=f"role_{uname}"
                            )
                        with col_pwd:
                            edit_password = st.text_input(
                                "Nova Senha (opcional)",
                                type="password",
                                placeholder="Deixe em branco para não alterar",
                                key=f"pwd_{uname}"
                            )

                        col_save, col_delete = st.columns(2)
                        with col_save:
                            submit_edit = st.form_submit_button("💾 Salvar", type="primary", use_container_width=True)
                        with col_delete:
                            submit_delete = st.form_submit_button("🗑️ Excluir", use_container_width=True)

                        if submit_edit:
                            try:
                                config['credentials']['usernames'][uname]['name'] = edit_name
                                config['credentials']['usernames'][uname]['email'] = edit_email
                                config['credentials']['usernames'][uname]['role'] = edit_role

                                msg_parts = [f"Usuário '{uname}' atualizado com sucesso!"]

                                if edit_password:
                                    import streamlit_authenticator as stauth
                                    hashed_pw = stauth.Hasher([edit_password]).generate()[0]
                                    config['credentials']['usernames'][uname]['password'] = hashed_pw
                                    msg_parts.append("Senha alterada.")

                                save_auth_config(config)
                                st.session_state.user_update_success = " ".join(msg_parts)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao atualizar usuário: {e}")

                        if submit_delete:
                            if uname == username:
                                st.error("❌ Você não pode excluir seu próprio usuário!")
                            else:
                                try:
                                    del config['credentials']['usernames'][uname]
                                    save_auth_config(config)
                                    st.session_state.user_delete_success = f"Usuário '{uname}' excluído com sucesso!"
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Erro ao excluir usuário: {e}")

    else:
        # Usuários não-admin: apenas visualização
        st.markdown("### 📊 Base de Aderência")
        ADHERENCE_PATH = Path("config/Aderencia.xlsm")

        if ADHERENCE_PATH.exists():
            st.info("✅ Base de aderência está configurada no sistema")
        else:
            st.warning("⚠️ Base de aderência não configurada. Contate o administrador.")

    st.markdown("---")
    st.markdown("### Gerenciar Dados")

    # Apenas admin pode limpar histórico
    if user_role == 'admin':
        if st.button("🗑️ Limpar histórico de análises"):
            if st.checkbox("Confirmo que quero apagar todo o meu histórico"):
                st.error("⚠️ Esta funcionalidade ainda não está implementada")
    else:
        st.info("💡 Apenas administradores podem gerenciar o histórico de análises.")

    st.markdown("---")
    st.markdown("### Sobre")
    st.info("""
    **IDT Analyzer v2.0**

    Ferramenta de análise de aderência do pré-diagnóstico IDT.

    - ✅ Análise de NCM × UF (Compras e Vendas)
    - ✅ Cobertura de municípios ISS
    - ✅ Alertas de CFOPs não-standard
    - ✅ Histórico de análises
    - ✅ Exportação Excel e PDF
    - ✅ Autenticação e controle de acesso

    **Thomson Reuters | 2024**
    """)
