"""
Translations for IDT Analyzer
Support for Portuguese and English
"""

TRANSLATIONS = {
    "pt": {
        # Authentication
        "auth_error": "❌ Usuário ou senha incorretos",
        "auth_warning": "⚠️ Por favor, faça login para acessar o sistema",
        "config_not_found": "❌ Arquivo config_auth.yaml não encontrado!",
        "generate_password_info": "Execute: python generate_password.py para gerar senhas",

        # Sidebar
        "welcome": "Bem-vindo",
        "logout": "Sair",
        "navigation": "Navegação",
        "new_analysis": "▸ Nova Análise",
        "history": "▸ Histórico",
        "settings": "▸ Configurações",
        "user": "Usuário",
        "profile": "Perfil",

        # Page titles
        "page_title": "Thomson Reuters | IDT Analyzer",
        "main_title": "IDT Pre-Diagnóstico — Analisador de Aderência",
        "subtitle": "Análise de aderência automatizada para propostas comerciais",

        # New Analysis Page
        "upload_section": "📤 Upload de Arquivos",
        "upload_base": "Base de Aderência (obrigatório)",
        "upload_base_help": "Planilha com os critérios de aderência",
        "upload_proposal": "Proposta Comercial",
        "upload_proposal_help": "Planilha da proposta a ser analisada",
        "analyze_button": "🔍 Analisar Aderência",
        "analyzing": "Analisando...",
        "analysis_complete": "✅ Análise concluída com sucesso!",

        # Results
        "results_title": "📊 Resultados da Análise",
        "overall_score": "Pontuação Geral",
        "coverage": "Cobertura",
        "missing_items": "Itens Faltantes",
        "municipalities": "Municípios",
        "covered": "Cobertos",
        "not_covered": "Não Cobertos",
        "download_pdf": "📄 Baixar Relatório PDF",
        "save_history": "💾 Salvar no Histórico",
        "saved_success": "✅ Análise salva no histórico!",

        # History Page
        "history_title": "📋 Histórico de Análises",
        "no_history": "Nenhuma análise no histórico ainda.",
        "filter_user": "Filtrar por Usuário",
        "all_users": "Todos",
        "filter_date": "Filtrar por Data",
        "all_dates": "Todas",
        "search_placeholder": "Buscar por cliente...",
        "date": "Data",
        "client": "Cliente",
        "score": "Pontuação",
        "analyzed_by": "Analisado por",
        "actions": "Ações",
        "view": "Ver",
        "delete": "Excluir",
        "confirm_delete": "Confirmar exclusão",
        "deleted_success": "✅ Análise excluída com sucesso!",

        # Settings Page
        "settings_title": "⚙️ Configurações",
        "change_password": "Alterar Senha",
        "current_password": "Senha Atual",
        "new_password": "Nova Senha",
        "confirm_password": "Confirmar Nova Senha",
        "update_password": "Atualizar Senha",
        "password_mismatch": "❌ As senhas não coincidem",
        "password_updated": "✅ Senha atualizada com sucesso!",
        "invalid_password": "❌ Senha atual incorreta",

        # Details
        "client_name": "Nome do Cliente",
        "proposal_date": "Data da Proposta",
        "observations": "Observações",
        "detailed_results": "Resultados Detalhados",
        "dimension": "Dimensão",
        "items_covered": "Itens Cobertos",
        "total_items": "Total de Itens",
        "coverage_percentage": "Cobertura (%)",
        "missing_items_list": "Itens Faltantes",

        # Errors
        "error_upload": "❌ Por favor, faça upload dos arquivos necessários",
        "error_analysis": "❌ Erro ao processar análise",
        "error_save": "❌ Erro ao salvar no histórico",
        "error_delete": "❌ Erro ao excluir análise",
        "error_pdf": "❌ Erro ao gerar PDF",

        # Language
        "language": "Idioma",
        "portuguese": "🇧🇷 Português",
        "english": "🇺🇸 English",
    },

    "en": {
        # Authentication
        "auth_error": "❌ Incorrect username or password",
        "auth_warning": "⚠️ Please login to access the system",
        "config_not_found": "❌ config_auth.yaml file not found!",
        "generate_password_info": "Run: python generate_password.py to generate passwords",

        # Sidebar
        "welcome": "Welcome",
        "logout": "Logout",
        "navigation": "Navigation",
        "new_analysis": "▸ New Analysis",
        "history": "▸ History",
        "settings": "▸ Settings",
        "user": "User",
        "profile": "Profile",

        # Page titles
        "page_title": "Thomson Reuters | IDT Analyzer",
        "main_title": "IDT Pre-Diagnosis — Adherence Analyzer",
        "subtitle": "Automated adherence analysis for commercial proposals",

        # New Analysis Page
        "upload_section": "📤 File Upload",
        "upload_base": "Adherence Base (required)",
        "upload_base_help": "Spreadsheet with adherence criteria",
        "upload_proposal": "Commercial Proposal",
        "upload_proposal_help": "Proposal spreadsheet to be analyzed",
        "analyze_button": "🔍 Analyze Adherence",
        "analyzing": "Analyzing...",
        "analysis_complete": "✅ Analysis completed successfully!",

        # Results
        "results_title": "📊 Analysis Results",
        "overall_score": "Overall Score",
        "coverage": "Coverage",
        "missing_items": "Missing Items",
        "municipalities": "Municipalities",
        "covered": "Covered",
        "not_covered": "Not Covered",
        "download_pdf": "📄 Download PDF Report",
        "save_history": "💾 Save to History",
        "saved_success": "✅ Analysis saved to history!",

        # History Page
        "history_title": "📋 Analysis History",
        "no_history": "No analysis in history yet.",
        "filter_user": "Filter by User",
        "all_users": "All",
        "filter_date": "Filter by Date",
        "all_dates": "All",
        "search_placeholder": "Search by client...",
        "date": "Date",
        "client": "Client",
        "score": "Score",
        "analyzed_by": "Analyzed by",
        "actions": "Actions",
        "view": "View",
        "delete": "Delete",
        "confirm_delete": "Confirm deletion",
        "deleted_success": "✅ Analysis deleted successfully!",

        # Settings Page
        "settings_title": "⚙️ Settings",
        "change_password": "Change Password",
        "current_password": "Current Password",
        "new_password": "New Password",
        "confirm_password": "Confirm New Password",
        "update_password": "Update Password",
        "password_mismatch": "❌ Passwords do not match",
        "password_updated": "✅ Password updated successfully!",
        "invalid_password": "❌ Incorrect current password",

        # Details
        "client_name": "Client Name",
        "proposal_date": "Proposal Date",
        "observations": "Observations",
        "detailed_results": "Detailed Results",
        "dimension": "Dimension",
        "items_covered": "Covered Items",
        "total_items": "Total Items",
        "coverage_percentage": "Coverage (%)",
        "missing_items_list": "Missing Items",

        # Errors
        "error_upload": "❌ Please upload the required files",
        "error_analysis": "❌ Error processing analysis",
        "error_save": "❌ Error saving to history",
        "error_delete": "❌ Error deleting analysis",
        "error_pdf": "❌ Error generating PDF",

        # Language
        "language": "Language",
        "portuguese": "🇧🇷 Português",
        "english": "🇺🇸 English",
    }
}


def get_translation(key: str, lang: str = "pt") -> str:
    """
    Get translation for a given key

    Args:
        key: Translation key
        lang: Language code ('pt' or 'en')

    Returns:
        Translated string
    """
    return TRANSLATIONS.get(lang, TRANSLATIONS["pt"]).get(key, key)


def get_all_translations(lang: str = "pt") -> dict:
    """
    Get all translations for a language

    Args:
        lang: Language code ('pt' or 'en')

    Returns:
        Dictionary with all translations
    """
    return TRANSLATIONS.get(lang, TRANSLATIONS["pt"])
