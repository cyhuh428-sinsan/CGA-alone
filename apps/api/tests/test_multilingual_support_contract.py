from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.auth import SignupRequestPayload
from app.schemas.bot import BotCreateRequest, BotUpdateRequest


ROOT_DIR = Path(__file__).resolve().parents[3]
SUPPORTED_LANGUAGES = ("ko", "en", "zh-CN", "ja", "vi", "fr", "de")
VISIBLE_LITERAL_COMPONENTS = (
    "conversation-message-settings-page.tsx",
    "conversation-default-settings-page.tsx",
    "smalltalk-settings-page.tsx",
    "blocklist-settings-page.tsx",
    "rule-settings-page.tsx",
    "botstation-settings-page.tsx",
    "messenger-settings-page.tsx",
    "messenger-floating-buttons-page.tsx",
    "messenger-recommended-intents-page.tsx",
    "bot-hub-create-form.tsx",
    "bot-hub-settings.tsx",
    "bot-hub-home.tsx",
    "bot-hub-composition.tsx",
    "bot-hub-retraining-page.tsx",
)


def test_remaining_settings_and_hub_pages_have_no_direct_korean_ui_literals() -> None:
    """Visible labels must pass through the locale catalog, not remain fixed Korean."""

    components_dir = ROOT_DIR / "apps" / "web" / "components"
    violations: list[str] = []
    attribute_pattern = __import__("re").compile(
        r'(?:title|description|help|placeholder|aria-label|label)="[^"]*[가-힣][^"]*"'
    )
    child_pattern = __import__("re").compile(r">[^<>{\n]*[가-힣][^<>{\n]*<")

    for filename in VISIBLE_LITERAL_COMPONENTS:
        source = (components_dir / filename).read_text(encoding="utf-8")
        for line_number, line in enumerate(source.splitlines(), start=1):
            if attribute_pattern.search(line) or child_pattern.search(line):
                violations.append(f"{filename}:{line_number}:{line.strip()}")

    assert not violations, "Direct Korean UI literals remain:\n" + "\n".join(violations)


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_bot_create_accepts_every_supported_language(language: str) -> None:
    payload = BotCreateRequest(name="multilingual bot", language=language)

    assert payload.language == language


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_bot_update_accepts_every_supported_language(language: str) -> None:
    payload = BotUpdateRequest(language=language)

    assert payload.language == language


def test_bot_language_rejects_unsupported_code() -> None:
    with pytest.raises(ValidationError):
        BotCreateRequest(name="unsupported locale bot", language="es")


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_signup_accepts_every_supported_preferred_language(language: str) -> None:
    payload = SignupRequestPayload(
        login_id="multilingual.user",
        password="Password!1",
        password_confirm="Password!1",
        name="Multilingual User",
        preferred_language=language,
        group_id="00000000-0000-0000-0000-000000000001",
    )

    assert payload.preferred_language == language


def test_web_language_contract_exposes_all_supported_languages() -> None:
    language_source = (ROOT_DIR / "apps/web/lib/language.ts").read_text(encoding="utf-8")

    for language in SUPPORTED_LANGUAGES:
        assert f'code: "{language}"' in language_source


def test_bot_create_and_settings_use_shared_language_options() -> None:
    create_source = (ROOT_DIR / "apps/web/components/bot-create-dialog.tsx").read_text(encoding="utf-8")
    settings_source = (ROOT_DIR / "apps/web/components/bot-settings-page.tsx").read_text(encoding="utf-8")

    assert "SUPPORTED_LANGUAGES" in create_source
    assert "getLanguageLabel" in settings_source


def test_header_and_account_menu_use_shared_language_options() -> None:
    header_source = (ROOT_DIR / "apps/web/components/cga-studio-header.tsx").read_text(encoding="utf-8")
    rail_source = (ROOT_DIR / "apps/web/components/studio-rail.tsx").read_text(encoding="utf-8")

    assert "SUPPORTED_LANGUAGES" in header_source
    assert "SUPPORTED_LANGUAGES" in rail_source


def test_root_layout_installs_shared_language_provider() -> None:
    layout_source = (ROOT_DIR / "apps/web/app/layout.tsx").read_text(encoding="utf-8")

    assert "LanguageProvider" in layout_source
    assert "<LanguageProvider>" in layout_source


def test_every_ui_catalog_has_the_same_translation_keys() -> None:
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/catalogs.ts").read_text(encoding="utf-8")

    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, TranslationCatalog>" in catalog_source


def test_header_rail_and_login_share_reactive_ui_language() -> None:
    header_source = (ROOT_DIR / "apps/web/components/cga-studio-header.tsx").read_text(encoding="utf-8")
    rail_source = (ROOT_DIR / "apps/web/components/studio-rail.tsx").read_text(encoding="utf-8")
    login_source = (ROOT_DIR / "apps/web/app/login/page.tsx").read_text(encoding="utf-8")

    for source in (header_source, rail_source, login_source):
        assert "useI18n" in source
    assert "window.localStorage.setItem(UI_LANGUAGE_STORAGE_KEY" not in header_source
    assert "window.localStorage.setItem(UI_LANGUAGE_STORAGE_KEY" not in rail_source


def test_login_language_selector_has_localized_accessible_name() -> None:
    login_source = (ROOT_DIR / "apps/web/app/login/page.tsx").read_text(encoding="utf-8")

    assert 'aria-label={t("common.language")}' in login_source


def test_signup_and_language_settings_use_shared_language_contract() -> None:
    signup_source = (ROOT_DIR / "apps/web/app/signup/page.tsx").read_text(encoding="utf-8")
    settings_source = (ROOT_DIR / "apps/web/app/me/language/page.tsx").read_text(encoding="utf-8")

    assert "preferred_language: language" in signup_source
    assert "SUPPORTED_LANGUAGES" in signup_source
    assert "useI18n" in settings_source
    assert "SUPPORTED_LANGUAGES" in settings_source


def test_bot_management_uses_complete_seven_language_catalog() -> None:
    management_source = (ROOT_DIR / "apps/web/components/bot-management-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/bot-management.ts").read_text(encoding="utf-8")

    assert "useI18n" in management_source
    assert "BOT_MANAGEMENT_CATALOGS[language]" in management_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, BotManagementCatalog>" in catalog_source


def test_bot_operations_workspace_uses_complete_seven_language_catalog() -> None:
    workspace_source = (ROOT_DIR / "apps/web/components/bot-operations-workspace-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/bot-workspace.ts").read_text(encoding="utf-8")

    assert "useI18n" in workspace_source
    assert "BOT_WORKSPACE_CATALOGS[language]" in workspace_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, BotWorkspaceCatalog>" in catalog_source


def test_bot_create_uses_localized_ai_options_and_seven_language_catalog() -> None:
    create_source = (ROOT_DIR / "apps/web/components/bot-create-dialog.tsx").read_text(encoding="utf-8")
    create_catalog_source = (ROOT_DIR / "apps/web/lib/i18n/bot-create.ts").read_text(encoding="utf-8")
    ai_catalog_source = (ROOT_DIR / "apps/web/lib/i18n/ai-options.ts").read_text(encoding="utf-8")

    assert "useI18n" in create_source
    assert "BOT_CREATE_CATALOGS[uiLanguage]" in create_source
    assert "translateAiOptionText(uiLanguage" in create_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in create_catalog_source or f"  {language}:" in create_catalog_source
        assert f'  "{language}":' in ai_catalog_source or f"  {language}:" in ai_catalog_source
    assert "satisfies Record<SupportedLanguage, BotCreateCatalog>" in create_catalog_source
    assert "satisfies Record<SupportedLanguage, AiOptionTranslationCatalog>" in ai_catalog_source


def test_bot_name_validation_accepts_unicode_letters_and_numbers() -> None:
    create_source = (ROOT_DIR / "apps/web/components/bot-create-dialog.tsx").read_text(encoding="utf-8")

    assert r"\p{L}\p{N}" in create_source
    assert "[가-힣a-zA-Z0-9" not in create_source


def test_bot_settings_uses_localized_catalog_and_unicode_bot_names() -> None:
    settings_source = (ROOT_DIR / "apps/web/components/bot-settings-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/bot-settings.ts").read_text(encoding="utf-8")

    assert "useI18n" in settings_source
    assert "BOT_SETTINGS_CATALOGS[uiLanguage]" in settings_source
    assert "translateAiOptionText(uiLanguage" in settings_source
    assert r"\p{L}\p{N}" in settings_source
    assert "[가-힣a-zA-Z0-9" not in settings_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, BotSettingsCatalog>" in catalog_source


def test_bot_settings_shell_uses_shared_navigation_and_localized_messages() -> None:
    shell_source = (ROOT_DIR / "apps/web/components/bot-settings-shell.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/bot-settings-shell.ts").read_text(encoding="utf-8")

    assert "useI18n" in shell_source
    assert "SHELL_NAVIGATION[uiLanguage]" in shell_source
    assert "BOT_SETTINGS_SHELL_CATALOGS[uiLanguage]" in shell_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, BotSettingsShellCatalog>" in catalog_source


def test_shared_training_header_uses_seven_language_catalog() -> None:
    button_source = (ROOT_DIR / "apps/web/components/nlu-training-button.tsx").read_text(encoding="utf-8")
    header_source = (ROOT_DIR / "apps/web/components/bot-workspace-header.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/training.ts").read_text(encoding="utf-8")

    assert "useI18n" in button_source
    assert "TRAINING_CATALOGS[uiLanguage]" in button_source
    assert "useI18n" in header_source
    assert "TRAINING_CATALOGS[uiLanguage]" in header_source
    assert "translateAiOptionText(uiLanguage" in header_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, TrainingCatalog>" in catalog_source


def test_intent_list_uses_seven_language_catalog_without_changing_csv_contract() -> None:
    page_source = (ROOT_DIR / "apps/web/components/intent-list-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/intent-list.ts").read_text(encoding="utf-8")
    import_source = (ROOT_DIR / "apps/web/lib/intent-import.ts").read_text(encoding="utf-8")

    assert "useI18n" in page_source
    assert "INTENT_LIST_CATALOGS[uiLanguage]" in page_source
    assert "formatIntentListText(" in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, IntentListCatalog>" in catalog_source
    assert '["의도명", "표시명", "의도 Key", "학습문장", "태그", "답변"]' in import_source
    assert "buildIntentUploadTemplateCsv()" in page_source
    assert '["의도명", "Intent Name", "intentName", "name"]' in import_source


def test_intent_list_localizes_delete_copy_and_preserves_reference_checks() -> None:
    page_source = (ROOT_DIR / "apps/web/components/intent-list-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/intent-list.ts").read_text(encoding="utf-8")

    assert "copy.deleteDialogTitle" in page_source
    assert "copy.deleteDialogQuestion" in page_source
    assert "copy.deleteReferenced" in page_source
    assert "findDialogUsageReferences" in page_source
    assert "persistVersionDocument" in page_source
    assert "deleteDialogTitle: string" in catalog_source
    assert "deleteReferenced: string" in catalog_source


def test_intent_csv_ui_is_localized_without_translating_csv_headers() -> None:
    page_source = (ROOT_DIR / "apps/web/components/intent-list-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/intent-list.ts").read_text(encoding="utf-8")
    import_source = (ROOT_DIR / "apps/web/lib/intent-import.ts").read_text(encoding="utf-8")

    assert "copy.uploadTitle" in page_source
    assert "copy.uploadResultTitle" in page_source
    assert "copy.addedIntents" in page_source
    assert 'const rows = [["의도명", "표시명", "의도 Key", "학습문장", "태그", "답변"]];' in import_source
    assert "buildIntentDownloadCsv(dialogs, answersByDialogId)" in page_source
    assert '["의도명", "Intent Name", "intentName", "name"]' in import_source
    assert "uploadTitle: string" in catalog_source


def test_intent_scenario_errors_localize_guidance_without_changing_training_blocking() -> None:
    page_source = (ROOT_DIR / "apps/web/components/intent-list-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/intent-list.ts").read_text(encoding="utf-8")

    assert "copy.scenarioIssueFallback" in page_source
    assert "copy.trainingBlockedByScenarioErrors" in page_source
    assert "scenarioErrorCount" in page_source
    assert "trainingDisabledReason" in page_source
    assert "scenarioIssueFallback: string" in catalog_source


def test_admin_navigation_and_shell_use_complete_seven_language_catalog() -> None:
    layout_source = (ROOT_DIR / "apps/web/components/admin-console-layout.tsx").read_text(encoding="utf-8")
    rail_source = (ROOT_DIR / "apps/web/components/studio-rail.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-navigation.ts").read_text(encoding="utf-8")

    for source in (layout_source, rail_source):
        assert "ADMIN_NAVIGATION_CATALOGS[language]" in source
        assert "buildAdminNavigationGroups(" in source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, AdminNavigationCatalog>" in catalog_source


def test_shared_admin_components_use_complete_localized_controls() -> None:
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-common.ts").read_text(encoding="utf-8")
    component_paths = (
        "apps/web/components/admin-table-page.tsx",
        "apps/web/components/admin-interactive-table-page.tsx",
        "apps/web/components/admin-history-table-page.tsx",
        "apps/web/components/admin-botstation-status-page.tsx",
    )
    for path in component_paths:
        source = (ROOT_DIR / path).read_text(encoding="utf-8")
        assert "ADMIN_COMMON_CATALOGS[language]" in source
    assert "satisfies Record<SupportedLanguage, AdminCommonCatalog>" in catalog_source


def test_primary_admin_history_routes_use_seven_language_page_catalog() -> None:
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-pages.ts").read_text(encoding="utf-8")
    for path in (
        "apps/web/app/admin/api-call-history/page.tsx",
        "apps/web/app/admin/bot-status/page.tsx",
        "apps/web/app/admin/login-history/page.tsx",
        "apps/web/app/admin/training-history/page.tsx",
        "apps/web/app/admin/intent-feedback/page.tsx",
    ):
        source = (ROOT_DIR / path).read_text(encoding="utf-8")
        assert "ADMIN_PAGE_CATALOGS[language]" in source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, AdminPageCatalog>" in catalog_source


def test_default_message_admin_screen_uses_language_filter_and_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/default-messages/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/default-messages.ts").read_text(encoding="utf-8")
    assert "SUPPORTED_LANGUAGES" in page_source
    assert "language: appliedLanguage" in page_source
    assert "DEFAULT_MESSAGES_CATALOGS[uiLanguage]" in page_source
    assert "satisfies Record<SupportedLanguage, DefaultMessagesCatalog>" in catalog_source


def test_bot_test_uses_seven_language_catalog_and_preserves_trace_data() -> None:
    page_source = (ROOT_DIR / "apps/web/components/simulator-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/simulator.ts").read_text(encoding="utf-8")
    assert "SIMULATOR_CATALOGS[uiLanguage]" in page_source
    assert "copy.botTestBreadcrumb" in page_source
    assert "copy.botTestTitle" in page_source
    assert "copy.analysisData" in page_source
    assert "selectedAnalysis.variableSnapshots" in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, SimulatorCatalog>" in catalog_source


def test_group_api_management_uses_seven_language_catalog() -> None:
    list_source = (ROOT_DIR / "apps/web/components/group-api-list-page.tsx").read_text(encoding="utf-8")
    detail_source = (ROOT_DIR / "apps/web/components/group-api-detail-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/api-management.ts").read_text(encoding="utf-8")
    assert "API_MANAGEMENT_CATALOGS[uiLanguage]" in list_source
    assert "API_MANAGEMENT_CATALOGS[uiLanguage]" in detail_source
    assert "copy.search" in list_source
    assert "copy.methodDescription" in detail_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, ApiManagementCatalog>" in catalog_source


def test_api_editor_uses_seven_language_catalog() -> None:
    editor_source = (ROOT_DIR / "apps/web/components/api-store-list-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/api-editor.ts").read_text(encoding="utf-8")
    assert "API_EDITOR_CATALOGS[uiLanguage]" in editor_source
    assert "copy.samplePlaceholder" in editor_source
    assert "copy.invalidJson" in editor_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, ApiEditorCatalog>" in catalog_source


def test_common_variable_admin_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/common-variables/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-common-variables.ts").read_text(encoding="utf-8")
    assert "COMMON_VARIABLE_CATALOGS[uiLanguage]" in page_source
    assert "copy.searchPlaceholder" in page_source
    assert "copy.readOnly" in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, CommonVariableCatalog>" in catalog_source


def test_license_admin_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/license/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-license.ts").read_text(encoding="utf-8")
    assert "ADMIN_LICENSE_CATALOGS[uiLanguage]" in page_source
    assert "copy.upload" in page_source
    assert "copy.licenseDetails" in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, AdminLicenseCatalog>" in catalog_source


def test_channel_admin_list_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/channels/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-channels.ts").read_text(encoding="utf-8")
    assert "ADMIN_CHANNEL_CATALOGS[uiLanguage]" in page_source
    assert "copy.searchPlaceholder" in page_source
    assert "copy.connectionTest" in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'"{language}":' in catalog_source or f"{language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage,AdminChannelCatalog>" in catalog_source


def test_channel_admin_dialog_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/channels/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-channel-dialog.ts").read_text(encoding="utf-8")
    assert "ADMIN_CHANNEL_DIALOG_CATALOGS[uiLanguage]" in page_source
    assert "dialogCopy.kakaoGuideTitle" in page_source
    assert "dialogCopy.authJsonHelp" in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'"{language}":' in catalog_source or f"{language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage,AdminChannelDialogCatalog>" in catalog_source


def test_template_admin_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/templates/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-templates.ts").read_text(encoding="utf-8")
    assert "ADMIN_TEMPLATE_CATALOGS[uiLanguage]" in page_source
    assert "copy.searchPlaceholder" in page_source
    assert "copy.kakaoGuideTitle" in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'"{language}":' in catalog_source or f"{language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage,AdminTemplateCatalog>" in catalog_source


def test_conversation_history_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/conversations/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-conversations.ts").read_text(encoding="utf-8")
    assert "ADMIN_CONVERSATION_CATALOGS[uiLanguage]" in page_source
    assert "copy.diagnosticSummary" in page_source
    assert "copy.averageResponseTime" in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'"{language}":' in catalog_source or f"{language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage,AdminConversationCatalog>" in catalog_source


def test_queue_history_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/queue-history/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-queue-history.ts").read_text(encoding="utf-8")
    assert "ADMIN_QUEUE_HISTORY_CATALOGS[uiLanguage]" in page_source
    assert "copy.processQueued" in page_source
    assert "copy.requestParameters" in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'"{language}":' in catalog_source or f"{language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage,AdminQueueHistoryCatalog>" in catalog_source


def test_audit_log_admin_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/audit-logs/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-audit-logs.ts").read_text(encoding="utf-8")
    assert "ADMIN_AUDIT_LOG_CATALOGS[uiLanguage]" in page_source
    assert "copy.auditDetailTitle" in page_source
    assert "copy.systemDetailTitle" in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'"{language}":' in catalog_source or f"{language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage,AdminAuditLogCatalog>" in catalog_source


def test_operations_dashboard_shell_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/operations-dashboard/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-operations-dashboard.ts").read_text(encoding="utf-8")
    assert "ADMIN_OPERATIONS_DASHBOARD_CATALOGS[uiLanguage]" in page_source
    assert "copy.title" in page_source
    assert "copy.cacheStatus" in page_source
    assert "copy.systemErrorsTitle" in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'"{language}":' in catalog_source or f"{language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage,AdminOperationsDashboardCatalog>" in catalog_source


def test_operations_dashboard_actions_use_localized_messages() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/operations-dashboard/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-operations-actions.ts").read_text(encoding="utf-8")
    assert "actionCopy.forceRelease" in page_source
    assert "actionCopy.cachePurgeConfirm" in page_source
    assert "actionCopy.dbBackfillConfirm" in page_source
    assert "formatOperationsText" in page_source
    assert "satisfies Record<SupportedLanguage,AdminOperationsActionCatalog>" in catalog_source


def test_operations_dashboard_status_cards_use_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/operations-dashboard/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-operations-status.ts").read_text(encoding="utf-8")
    assert "statusCopy.summaryLabels" in page_source
    assert "statusCopy.detail" in page_source
    assert "statusCopy.loginRequired" in page_source
    assert "statusCopy.health.apiReadiness" in page_source
    assert "satisfies Record<SupportedLanguage, AdminOperationsStatusCatalog>" in catalog_source


def test_operations_dashboard_tables_and_details_use_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/operations-dashboard/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-operations-details.ts").read_text(encoding="utf-8")
    assert "detailsCopy.cache.status" in page_source
    assert "detailsCopy.integrity.version" in page_source
    assert "detailsCopy.dialogs.operationsErrorTitle" in page_source
    assert "운영 오류 상세" not in page_source
    assert "satisfies Record<SupportedLanguage, AdminOperationsDetailsCatalog>" in catalog_source


def test_admin_users_list_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/users/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-users.ts").read_text(encoding="utf-8")
    assert "ADMIN_USERS_CATALOGS[uiLanguage]" in page_source
    assert "copy.accountStatuses[item.account_status]" in page_source
    assert "copy.roleNames[item.role_code]" in page_source
    assert "new Intl.DateTimeFormat(uiLanguage" in page_source
    assert "satisfies Record<SupportedLanguage, AdminUsersCatalog>" in catalog_source


def test_admin_groups_list_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/groups/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-groups.ts").read_text(encoding="utf-8")
    assert "ADMIN_GROUPS_CATALOGS[uiLanguage]" in page_source
    assert "copy.statuses[item.status]" in page_source
    assert "new Intl.DateTimeFormat(uiLanguage" in page_source
    assert "satisfies Record<SupportedLanguage, AdminGroupsCatalog>" in catalog_source


def test_admin_group_create_uses_selected_ui_language() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/groups/new/page.tsx").read_text(encoding="utf-8")
    assert "ADMIN_GROUPS_CATALOGS[uiLanguage]" in page_source
    assert "copy.createForm.title" in page_source
    assert "copy.createForm.submitError" in page_source


def test_admin_group_detail_uses_selected_ui_language() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/groups/[groupId]/page.tsx").read_text(encoding="utf-8")
    assert "ADMIN_GROUPS_CATALOGS[uiLanguage]" in page_source
    assert "copy.detailForm.title" in page_source
    assert "copy.statuses[status]" in page_source
    assert "new Intl.DateTimeFormat(uiLanguage" in page_source


def test_admin_user_detail_uses_selected_ui_language_and_preserves_status_compatibility() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/users/[entryId]/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-users.ts").read_text(encoding="utf-8")
    assert "ADMIN_USERS_CATALOGS[uiLanguage]" in page_source
    assert "copy.detailForm.title" in page_source
    assert "resolveAdminAccountStatus(data.account_status)" in page_source
    assert "copy.roleNames[selectedRole]" in page_source
    assert "LEGACY_ACCOUNT_STATUS_ALIASES" in catalog_source


def test_api_call_history_detail_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/api-call-history/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-api-call-history.ts").read_text(encoding="utf-8")
    assert "ADMIN_API_CALL_HISTORY_CATALOGS[language]" in page_source
    assert "detailCopy.dialogTitle" in page_source
    assert "detailCopy.requestData" in page_source
    assert "detailCopy.yes" in page_source
    assert "new Intl.DateTimeFormat(language" in page_source
    assert "API 호출 상세 이력" not in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, AdminApiCallHistoryCatalog>" in catalog_source


def test_intent_feedback_detail_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/intent-feedback/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-intent-feedback.ts").read_text(encoding="utf-8")
    assert "ADMIN_INTENT_FEEDBACK_CATALOGS[language]" in page_source
    assert "detailCopy.dialogTitle" in page_source
    assert "detailCopy.suggestedTrainingSentences" in page_source
    assert "formatIntentFeedbackCount" in page_source
    assert "의도 피드백 상세" not in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, AdminIntentFeedbackCatalog>" in catalog_source


def test_training_history_quality_panel_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/training-history/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-training-history.ts").read_text(encoding="utf-8")
    assert "ADMIN_TRAINING_HISTORY_CATALOGS[language]" in page_source
    assert "qualityCopy.semanticValidationTitle" in page_source
    assert "qualityCopy.nluQualityTitle" in page_source
    assert "new Intl.DateTimeFormat(language" in page_source
    assert "Semantic NLU 학습문장 자기검증" not in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, AdminTrainingHistoryCatalog>" in catalog_source


def test_remaining_admin_list_ui_uses_selected_language() -> None:
    login_source = (ROOT_DIR / "apps/web/app/admin/login-history/page.tsx").read_text(encoding="utf-8")
    messages_source = (ROOT_DIR / "apps/web/app/admin/default-messages/page.tsx").read_text(encoding="utf-8")
    bot_source = (ROOT_DIR / "apps/web/app/admin/bot-status/page.tsx").read_text(encoding="utf-8")
    common_source = (ROOT_DIR / "apps/web/lib/i18n/admin-common.ts").read_text(encoding="utf-8")
    assert "new Intl.DateTimeFormat(language" in login_source
    assert "new Intl.DateTimeFormat(uiLanguage" in messages_source
    assert "formatAdminText(commonCopy.selectItem" in bot_source
    assert "selectItem: string" in common_source
    assert 'Intl.DateTimeFormat("ko-KR"' not in login_source
    assert 'Intl.DateTimeFormat("ko-KR"' not in messages_source


def test_template_renderer_defaults_follow_selected_language() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/templates/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-template-defaults.ts").read_text(encoding="utf-8")
    assert "ADMIN_TEMPLATE_DEFAULT_CATALOGS[uiLanguage]" in page_source
    assert "rendererDefaults" in page_source
    assert 'description: "기본 텍스트 메시지"' not in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, AdminTemplateDefaultCatalog>" in catalog_source


def test_account_pages_use_seven_language_catalog() -> None:
    signup_source = (ROOT_DIR / "apps/web/app/signup/page.tsx").read_text(encoding="utf-8")
    profile_source = (ROOT_DIR / "apps/web/app/me/profile/page.tsx").read_text(encoding="utf-8")
    password_source = (ROOT_DIR / "apps/web/app/me/password/page.tsx").read_text(encoding="utf-8")
    language_source = (ROOT_DIR / "apps/web/app/me/language/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/account-pages.ts").read_text(encoding="utf-8")
    assert "ACCOUNT_PAGE_CATALOGS[language].signup" in signup_source
    assert "ACCOUNT_PAGE_CATALOGS[language].profile" in profile_source
    assert "ACCOUNT_PAGE_CATALOGS[language].password" in password_source
    assert "ACCOUNT_PAGE_CATALOGS[language].language" in language_source
    assert "getAccountRoleLabel" in profile_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, AccountPageCatalog>" in catalog_source


def test_studio_rail_getting_started_uses_seven_language_catalog() -> None:
    rail_source = (ROOT_DIR / "apps/web/components/studio-rail.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/studio-rail.ts").read_text(encoding="utf-8")
    assert "STUDIO_RAIL_CATALOGS[language]" in rail_source
    assert "railCopy.gettingStartedSlides" in rail_source
    assert "railCopy.noPermission" in rail_source
    assert "getAccountRoleLabel" in rail_source
    assert "쉽고 빠르게 AI 챗봇을 만들 수 있습니다." not in rail_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, StudioRailCatalog>" in catalog_source


def test_entity_list_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/entity-list-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/entity-list.ts").read_text(encoding="utf-8")
    assert "ENTITY_LIST_CATALOGS[uiLanguage]" in page_source
    assert "copy.searchPlaceholder" in page_source
    assert "copy.uploadResultTitle" in page_source
    assert "copy.columns.category" in page_source
    assert 'title="파일 업로드"' not in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, EntityListCatalog>" in catalog_source


def test_intent_list_sorting_uses_selected_ui_language() -> None:
    page_source = (ROOT_DIR / "apps/web/components/intent-list-page.tsx").read_text(encoding="utf-8")
    assert "localeCompare(right, uiLanguage)" in page_source
    assert 'localeCompare(right, "ko-KR")' not in page_source


def test_dictionary_list_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/dictionary-list-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/dictionary-list.ts").read_text(encoding="utf-8")
    assert "DICTIONARY_LIST_CATALOGS[uiLanguage]" in page_source
    assert "copy.searchPlaceholder" in page_source
    assert "copy.uploadResultTitle" in page_source
    assert "copy.columns.word" in page_source
    assert 'title="파일 업로드"' not in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, DictionaryListCatalog>" in catalog_source

def test_dictionary_editor_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/dictionary-editor-dialog.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/dictionary-editor.ts").read_text(encoding="utf-8")
    assert "DICTIONARY_EDITOR_CATALOGS[uiLanguage]" in page_source
    assert "copy.synonymRecommendation" in page_source
    assert "copy.validation.required" in page_source
    assert "copy.intentUsage" in page_source
    assert '>동의어 추천<' not in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, DictionaryEditorCatalog>" in catalog_source

def test_entity_name_dialog_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/entity-name-dialog.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/entity-name-dialog.ts").read_text(encoding="utf-8")
    assert "ENTITY_NAME_DIALOG_CATALOGS[uiLanguage]" in page_source
    assert "copy.validation.required" in page_source
    assert "copy.createTitle" in page_source
    assert '"개체명 추가"' not in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, EntityNameDialogCatalog>" in catalog_source

def test_entity_editor_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/entity-editor-dialog.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/entity-editor.ts").read_text(encoding="utf-8")
    assert "ENTITY_EDITOR_CATALOGS[uiLanguage]" in page_source
    assert "copy.validation.invalidRegex" in page_source
    assert "copy.dictionaryImportTitle" in page_source
    assert "copy.systemEntityDescription" in page_source
    assert 'aria-label="사전 불러오기"' not in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, EntityEditorCatalog>" in catalog_source

def test_entity_value_item_dialog_uses_selected_language() -> None:
    page_source = (ROOT_DIR / "apps/web/components/entity-editor-dialog.tsx").read_text(encoding="utf-8")
    assert "copy.valueCreateTitle" in page_source
    assert "copy.validation.valueRequired" in page_source
    assert "copy.regexTest" in page_source
    assert '"개체값 생성"' not in page_source
    assert '"등록 가능한 정규식입니다."' not in page_source

def test_studio_operations_dashboard_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/operations-dashboard-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/studio-operations-dashboard.ts").read_text(encoding="utf-8")
    assert "STUDIO_OPERATIONS_DASHBOARD_CATALOGS[language]" in page_source
    assert "copy.statuses[status]" in page_source
    assert "copy.roles[role]" in page_source
    assert "copy.recentUpdates" in page_source
    assert '"운영 대시보드"' not in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, StudioOperationsDashboardCatalog>" in catalog_source

def test_intent_editor_dialog_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/intent-editor-dialog.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/intent-editor.ts").read_text(encoding="utf-8")
    assert "INTENT_EDITOR_CATALOGS[uiLanguage]" in page_source
    assert "copy.validation.nameRequired" in page_source
    assert "copy.transitionLockedDescription" in page_source
    assert "copy.llmPrompt" in page_source
    assert '"의도/모듈명을 입력해주세요."' not in page_source
    assert 'aria-label="닫기"' not in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, IntentEditorCatalog>" in catalog_source

def test_intent_configure_input_panel_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/intent-configure-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/intent-configure-input.ts").read_text(encoding="utf-8")
    assert "INTENT_CONFIGURE_INPUT_CATALOGS[uiLanguage]" in page_source
    assert "inputCopy.operatingVersionWarning" in page_source
    assert "inputCopy.utterancePanelTitle" in page_source
    assert "formatIntentConfigureInputText" in page_source
    assert '>학습문장 입력<' not in page_source
    assert 'aria-label="분류 수 기준"' not in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, IntentConfigureInputCatalog>" in catalog_source

def test_intent_configure_candidate_panel_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/intent-configure-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/intent-configure-input.ts").read_text(encoding="utf-8")
    assert "inputCopy.mlTestTitle" in page_source
    assert "inputCopy.intentCandidates" in page_source
    assert "inputCopy.emptyUtterancePrompt" in page_source
    assert "inputCopy.overwriteVersion" in page_source
    assert '<strong>ML 구성 테스트</strong>' not in page_source
    assert '<strong>의도 후보</strong>' not in page_source
    assert "mlTestTitle: string" in catalog_source
    assert "emptyUtterancePrompt: string" in catalog_source

def test_intent_configure_seed_modal_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/intent-configure-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/intent-configure-input.ts").read_text(encoding="utf-8")
    assert "inputCopy.seedIntentEntry" in page_source
    assert "inputCopy.seedBulkDescription" in page_source
    assert "inputCopy.recognizedSeedCount" in page_source
    assert "inputCopy.seedPlaceholder" in page_source
    assert '<h2 id="intent-configure-seed-title">ML 기준 의도 입력</h2>' not in page_source
    assert 'aria-label="닫기" onClick={() => setMlSeedIntentOpen(false)}' not in page_source
    assert "seedIntentEntry: string" in catalog_source
    assert "seedEmptyHint: string" in catalog_source

def test_intent_configure_settings_modal_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/intent-configure-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/intent-configure-input.ts").read_text(encoding="utf-8")
    assert "inputCopy.settingsTitle" in page_source
    assert "inputCopy.recommendedNluCriteria" in page_source
    assert "inputCopy.autoClassificationWeights" in page_source
    assert "getIntentConfigureCriteriaLabel" in page_source
    assert '<h2 id="intent-configure-settings-title">NLU 기준 / 가중치 설정</h2>' not in page_source
    assert '<strong>자동분류 가중치</strong>' not in page_source
    assert "criteriaScale: {" in catalog_source
    assert "settingsTitle: string" in catalog_source

def test_intent_configure_ml_runtime_messages_use_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/intent-configure-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/intent-configure-input.ts").read_text(encoding="utf-8")
    assert "inputCopy.mlTestUtteranceRequired" in page_source
    assert "inputCopy.seedLoaded" in page_source
    assert "inputCopy.invalidSeedFormat" in page_source
    assert 'setErrorMessage("테스트할 사용자 발화를 입력해주세요.")' not in page_source
    assert 'setMessage(`현재 버전 의도 ${parsed.seedIntents.length}개를 ML 기준 의도로 불러왔습니다.`)' not in page_source
    assert "mlTestUtteranceRequired: string" in catalog_source
    assert "seedCleared: string" in catalog_source


def test_intent_configure_classification_runtime_messages_use_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/intent-configure-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/intent-configure-input.ts").read_text(encoding="utf-8")
    assert "inputCopy.classificationUtterancesRequired" in page_source
    assert "inputCopy.classificationPreparing" in page_source
    assert "inputCopy.classificationSummary" in page_source
    assert "inputCopy.mergeAtLeastTwo" in page_source
    assert "inputCopy.mergeComplete" in page_source
    assert 'setErrorMessage("분류할 학습문장을 입력해주세요.")' not in page_source
    assert 'setMessage("선택한 의도 후보를 병합했습니다.")' not in page_source
    assert "classificationUtterancesRequired: string" in catalog_source
    assert "classificationFailed: string" in catalog_source
    assert "mergeComplete: string" in catalog_source


def test_intent_configure_rag_runtime_messages_use_language_independent_progress_stage() -> None:
    page_source = (ROOT_DIR / "apps/web/components/intent-configure-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/intent-configure-input.ts").read_text(encoding="utf-8")
    assert 'type RagConfigureStage = "idle"' in page_source
    assert "ragConfigureStepFloorPercent(stage: RagConfigureStage)" in page_source
    assert 'setRagConfigureStage("embedding")' in page_source
    assert 'step.includes("임베딩")' not in page_source
    assert "inputCopy.ragAnswerModeOnly" in page_source
    assert "inputCopy.ragCandidatesCreated" in page_source
    assert 'setRagConfigureStep("Answer Vector DB에 답변 문서를 임베딩하는 중입니다.")' not in page_source
    assert "ragUploadPdf: string" in catalog_source
    assert "ragResultCompleted: string" in catalog_source
    assert "ragConfigureFailed: string" in catalog_source


def test_intent_configure_save_runtime_messages_use_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/intent-configure-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/intent-configure-input.ts").read_text(encoding="utf-8")
    assert "inputCopy.dictionarySuggestionsApplied" in page_source
    assert "inputCopy.scoringSaved" in page_source
    assert "inputCopy.criteriaApplied" in page_source
    assert "inputCopy.versionOverwritten" in page_source
    assert 'setErrorMessage("먼저 학습문장을 분류해주세요.")' not in page_source
    assert 'setMessage("구성 자동분류 가중치를 봇 설정에 저장했습니다.")' not in page_source
    assert "dictionarySuggestionsApplied: string" in catalog_source
    assert "criteriaApplied: string" in catalog_source
    assert "versionOverwritten: string" in catalog_source


def test_intent_configure_load_failure_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/intent-configure-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/intent-configure-input.ts").read_text(encoding="utf-8")
    assert "inputCopy.loadFailed" in page_source
    assert 'error.message : "구성 정보를 불러오지 못했습니다."' not in page_source
    assert "loadFailed: string" in catalog_source


def test_api_store_list_body_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/api-store-list-page.tsx").read_text(encoding="utf-8")
    assert "const common = API_MANAGEMENT_CATALOGS[uiLanguage]" in page_source
    assert "placeholder={common.search}" in page_source
    assert "aria-label={common.filter}" in page_source
    assert "{common.create}" in page_source
    assert "{common.downloadAll}" in page_source
    assert "common.category" in page_source
    assert "common.updatedBy" in page_source
    assert 'placeholder="API 이름 또는 목적지 Base URL을 검색하세요."' not in page_source
    assert 'label="API 이름"' not in page_source


def test_api_store_list_runtime_messages_use_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/api-store-list-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/api-management.ts").read_text(encoding="utf-8")
    assert "common.loadFailed" in page_source
    assert "common.downloadedSelected" in page_source
    assert "common.uploaded" in page_source
    assert "common.deletedSelected" in page_source
    assert 'setErrorMessage("API 등록 권한이 없습니다.")' not in page_source
    assert '"선택한 API가 삭제되었습니다."' not in page_source
    assert "loadFailed: string" in catalog_source
    assert "formatApiManagementText" in catalog_source


def test_api_store_detail_body_and_runtime_messages_use_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/api-store-detail-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/api-management.ts").read_text(encoding="utf-8")
    assert "const common = API_MANAGEMENT_CATALOGS[uiLanguage]" in page_source
    assert "common.detailTitle" in page_source
    assert "common.apiBasic" in page_source
    assert "common.updatedWithDesignNotice" in page_source
    assert "common.testFailed" in page_source
    assert '<span>API 조회</span>' not in page_source
    assert '<strong>API 등록기본</strong>' not in page_source
    assert 'setErrorMessage("API 삭제 권한이 없습니다.")' not in page_source
    assert "detailTitle: string" in catalog_source
    assert "updatedWithDesignNotice: string" in catalog_source
    assert "testFailed: string" in catalog_source

def test_group_api_list_runtime_messages_use_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/group-api-list-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/api-management.ts").read_text(encoding="utf-8")
    assert "copy.loginRequired" in page_source
    assert "copy.saveForbidden" in page_source
    assert "copy.uploadForbidden" in page_source
    assert "formatApiManagementText(copy.uploaded" in page_source
    assert 'setErrorMessage("로그인이 필요합니다.")' not in page_source
    assert '"선택한 API를 삭제했습니다."' not in page_source
    assert "loginRequired: string" in catalog_source
    assert "uploadForbidden: string" in catalog_source


def test_group_api_detail_runtime_and_table_labels_use_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/group-api-detail-page.tsx").read_text(encoding="utf-8")
    assert "copy.detailLoadFailed" in page_source
    assert "copy.deleteForbidden" in page_source
    assert "copy.testFailed" in page_source
    assert "<th>{copy.name}</th>" in page_source
    assert "<strong>{copy.testOutput}</strong>" in page_source
    assert 'setMessage("API가 수정되었습니다.")' not in page_source
    assert '<strong>Test Output</strong>' not in page_source

def test_admin_audit_log_detail_and_csv_use_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/app/admin/audit-logs/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-audit-logs.ts").read_text(encoding="utf-8")
    assert "downloadCsv(items, copy.auditExportColumns, locale)" in page_source
    assert "{copy.level}" in page_source
    assert "{copy.method}" in page_source
    assert 'const headers = ["작업", "대상", "대상 ID", "사용자", "IP", "발생일시", "요약"]' not in page_source
    assert "auditExportColumns:string[]" in catalog_source
    assert "level:string" in catalog_source
    assert "method:string" in catalog_source

def test_page_shell_and_utility_routes_use_seven_language_catalog() -> None:
    shell_source = (ROOT_DIR / "apps/web/components/page-shell.tsx").read_text(encoding="utf-8")
    license_source = (ROOT_DIR / "apps/web/app/license/page.tsx").read_text(encoding="utf-8")
    tenant_source = (ROOT_DIR / "apps/web/app/tenant-switch/page.tsx").read_text(encoding="utf-8")
    dashboard_source = (ROOT_DIR / "apps/web/app/studio/dashboard/page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/utility-pages.ts").read_text(encoding="utf-8")
    assert "PAGE_SHELL_CATALOGS[language]" in shell_source
    assert "UTILITY_PAGE_CATALOGS[language].license" in license_source
    assert "UTILITY_PAGE_CATALOGS[language].tenantSwitch" in tenant_source
    assert "UTILITY_PAGE_CATALOGS[language].dashboardPreparing" in dashboard_source
    assert '"매뉴얼 대응 항목"' not in shell_source
    assert 'title="라이선스 정보 조회"' not in license_source
    assert 'title="테넌트 전환"' not in tenant_source
    assert "satisfies Record<SupportedLanguage, UtilityPageCatalog>" in catalog_source

def test_analysis_page_uses_seven_language_catalog_without_changing_filter_keys() -> None:
    page_source = (ROOT_DIR / "apps/web/components/analysis-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/analysis.ts").read_text(encoding="utf-8")
    assert "const copy = ANALYSIS_CATALOGS[uiLanguage]" in page_source
    assert "getAnalysisMethodLabel(copy" in page_source
    assert "copy.responseOverviewTitle" in page_source
    assert "copy.selectedDateHistory" in page_source
    assert '<h3>전체 응답률 / 응답률 Top 3</h3>' not in page_source
    assert 'error.message : "분석 정보를 불러오지 못했습니다."' not in page_source
    assert 'value="제외/무시"' in page_source
    assert "satisfies Record<SupportedLanguage, AnalysisCatalog>" in catalog_source

def test_retraining_page_uses_seven_language_catalog_and_preserves_status_keys() -> None:
    page_source = (ROOT_DIR / "apps/web/components/retraining-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/retraining.ts").read_text(encoding="utf-8")
    assert "const copy = RETRAINING_CATALOGS[uiLanguage]" in page_source
    assert "getRetrainingOptionLabel(copy" in page_source
    assert "copy.searchPlaceholder" in page_source
    assert "copy.retrainingCandidates" in page_source
    assert 'setErrorMessage("재학습할 문장을 선택하세요.")' not in page_source
    assert 'updateRecordStatus("재학습제외")' in page_source
    assert 'type RetrainingStatus = "미학습" | "보류" | "재학습제외" | "재학습완료" | "삭제"' in page_source
    assert "satisfies Record<SupportedLanguage, RetrainingCatalog>" in catalog_source

def test_evaluation_page_uses_seven_language_catalog_without_changing_csv_compatibility() -> None:
    page_source = (ROOT_DIR / "apps/web/components/evaluation-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/evaluation.ts").read_text(encoding="utf-8")
    assert "const copy = EVALUATION_CATALOGS[uiLanguage]" in page_source
    assert "tEvaluation(copy" in page_source
    assert "copy.loadFailed" in page_source
    assert "copy.botEvaluation" in page_source
    assert 'setErrorMessage("평가 데이터에서 학습문장과 의도명을 찾지 못했습니다.")' not in page_source
    assert 'const rows = [["의도명", "학습문장"]]' in page_source
    assert "satisfies Record<SupportedLanguage, EvaluationCatalog>" in catalog_source

def test_version_management_page_uses_seven_language_catalog_without_changing_status_values() -> None:
    page_source = (ROOT_DIR / "apps/web/components/version-management-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/version-management.ts").read_text(encoding="utf-8")
    assert "const copy = VERSION_MANAGEMENT_CATALOGS[uiLanguage]" in page_source
    assert "getVersionManagementLabel(copy" in page_source
    assert "copy.loadFailed" in page_source
    assert 'selectedVersion.status === "active"' in page_source
    assert '<strong>버전 관리</strong>' not in page_source
    assert "satisfies Record<SupportedLanguage, VersionManagementCatalog>" in catalog_source

def test_flow_designer_uses_seven_language_catalog_without_changing_graph_contract() -> None:
    page_source = (ROOT_DIR / "apps/web/components/flow-designer-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/flow-designer.ts").read_text(encoding="utf-8")
    assert "FLOW_DESIGNER_CATALOGS[uiLanguage]" in page_source
    assert "getFlowDesignerLabel(copy" in page_source
    assert "copy.loadFailed" in page_source
    assert 'kind: "talk"' in page_source
    assert 'kind: "condition"' in page_source
    assert '<strong>대화 테스트</strong>' not in page_source
    assert 'placeholder="봇 메시지를 검색하세요."' not in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, FlowDesignerCatalog>" in catalog_source

def test_remaining_bot_settings_and_hub_pages_use_seven_language_studio_catalog() -> None:
    paths = (
        "apps/web/components/conversation-message-settings-page.tsx",
        "apps/web/components/conversation-default-settings-page.tsx",
        "apps/web/components/rule-settings-page.tsx",
        "apps/web/components/smalltalk-settings-page.tsx",
        "apps/web/components/blocklist-settings-page.tsx",
        "apps/web/components/botstation-settings-page.tsx",
        "apps/web/components/messenger-settings-page.tsx",
        "apps/web/components/messenger-floating-buttons-page.tsx",
        "apps/web/components/messenger-recommended-intents-page.tsx",
        "apps/web/components/bot-delete-page.tsx",
        "apps/web/components/bot-hub-create-form.tsx",
        "apps/web/components/bot-hub-home.tsx",
        "apps/web/components/bot-hub-settings.tsx",
        "apps/web/components/bot-hub-retraining-page.tsx",
        "apps/web/components/bot-hub-composition.tsx",
        "apps/web/components/bot-hub-delete.tsx",
    )
    for path in paths:
        source = (ROOT_DIR / path).read_text(encoding="utf-8")
        assert "useI18n" in source, path
        assert "STUDIO_PAGE_CATALOGS[uiLanguage]" in source, path
        assert "getStudioPageLabel(copy" in source, path

    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/studio-pages.ts").read_text(encoding="utf-8")
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, StudioPageCatalog>" in catalog_source

def test_core_shared_studio_components_use_language_context() -> None:
    paths = (
        "apps/web/components/bots-workspace.tsx",
        "apps/web/components/auth-session-toolbar.tsx",
        "apps/web/components/manual-main-version-select.tsx",
        "apps/web/components/asset-upload-dialog.tsx",
        "apps/web/components/studio-page-loading.tsx",
        "apps/web/components/studio-table-page.tsx",
        "apps/web/components/sort-header-label.tsx",
        "apps/web/components/upload-result-dialog.tsx",
    )
    for path in paths:
        source = (ROOT_DIR / path).read_text(encoding="utf-8")
        assert "useI18n" in source, path
        assert "STUDIO_PAGE_CATALOGS[uiLanguage]" in source, path
        assert "getStudioPageLabel(copy" in source, path

    bots_source = (ROOT_DIR / "apps/web/components/bots-workspace.tsx").read_text(encoding="utf-8")
    assert '>+ 봇/봇 허브 생성<' not in bots_source
    assert '>봇 목록을 불러오는 중입니다...<' not in bots_source


def test_conversation_and_flow_route_shells_delegate_visible_labels_to_client_catalog() -> None:
    studio_table = (ROOT_DIR / "apps/web/components/studio-table-page.tsx").read_text(encoding="utf-8")
    sort_header = (ROOT_DIR / "apps/web/components/sort-header-label.tsx").read_text(encoding="utf-8")
    assert "getStudioPageLabel(copy, title)" in studio_table
    assert "getStudioPageLabel(copy, searchPlaceholder)" in studio_table
    assert "getStudioPageLabel(copy, String(column))" in studio_table
    assert "getStudioPageLabel(copy, label)" in sort_header

def test_intent_start_page_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/intent-start-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/intent-start.ts").read_text(encoding="utf-8")
    assert "useI18n" in page_source
    assert "INTENT_START_CATALOGS[uiLanguage]" in page_source
    assert "copy.trainingSentenceSearch" in page_source
    assert "copy.extractEntities" in page_source
    assert 'placeholder="학습문장을 검색하세요."' not in page_source
    assert '<span>챗봇 메시지</span>' not in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, IntentStartCatalog>" in catalog_source

def test_admin_botstation_status_uses_seven_language_catalog() -> None:
    page_source = (ROOT_DIR / "apps/web/components/admin-botstation-status-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/admin-botstation-status.ts").read_text(encoding="utf-8")
    assert "ADMIN_BOTSTATION_STATUS_CATALOGS[uiLanguage]" in page_source
    assert "getAdminBotstationStatusLabel(stationCopy" in page_source
    assert '<h2>봇스테이션 연계 현황</h2>' not in page_source
    assert 'aria-label="검색 조건"' not in page_source
    assert 'status: "전체"' in page_source
    for language in SUPPORTED_LANGUAGES:
        assert f'  "{language}":' in catalog_source or f"  {language}:" in catalog_source
    assert "satisfies Record<SupportedLanguage, AdminBotstationStatusCatalog>" in catalog_source

def test_help_popover_links_all_seven_language_manual_pdfs() -> None:
    rail_source = (ROOT_DIR / "apps/web/components/studio-rail.tsx").read_text(encoding="utf-8")
    assert "manualHref(\"getting-started\")" in rail_source
    assert "manualHref(\"user-manual\")" in rail_source
    assert "manualHref(\"nlu-guide\")" in rail_source
    assert 'href="/manuals/cga-user-manual.pdf"' not in rail_source
    assert 'href="/manuals/cga-nlu-guide.pdf"' not in rail_source

    for language in SUPPORTED_LANGUAGES:
        for manual in ("getting-started", "user-manual", "nlu-guide"):
            assert (ROOT_DIR / f"apps/web/public/manuals/cga-{manual}-{language}.pdf").is_file()

    assert (ROOT_DIR / "apps/web/public/manuals/cga-user-manual.pdf").is_file()
    assert (ROOT_DIR / "apps/web/public/manuals/cga-nlu-guide.pdf").is_file()

def test_deep_studio_surfaces_localize_static_visible_text() -> None:
    simulator = (ROOT_DIR / "apps/web/components/simulator-page.tsx").read_text(encoding="utf-8")
    for literal in (
        '>이미지 열기</a>', '>표시할 항목이 없습니다.</p>', '>이전으로</button>',
        '<span>지도</span>', '<span>스카이뷰</span>', 'aria-label="팝업 열기"',
        'aria-label="닫기"', '>팝업에 표시할 데이터가 없습니다.</p>',
        '<option value="">선택하세요</option>',
    ):
        assert literal not in simulator
    assert "getSimulatorLabel(uiLanguage" in simulator

    workspace = (ROOT_DIR / "apps/web/components/studio-workspace-provider.tsx").read_text(encoding="utf-8")
    assert "useI18n" in workspace
    assert "getStudioPageLabel(copy" in workspace
    assert '>이 봇에는 등록된 버전이 없습니다.</strong>' not in workspace

    station = (ROOT_DIR / "apps/web/components/admin-botstation-status-page.tsx").read_text(encoding="utf-8")
    assert 'data-help="카카오 앱 또는 스킬 식별값입니다.' not in station
    assert 'data-help="카카오 webhook 보호용 비밀값입니다.' not in station
    assert 'data-help="카카오 관리자센터에 등록할 실제 webhook 주소입니다.' not in station

def test_server_route_labels_cross_a_localized_client_boundary() -> None:
    page_shell = (ROOT_DIR / "apps/web/components/page-shell.tsx").read_text(encoding="utf-8")
    table_page = (ROOT_DIR / "apps/web/components/studio-table-page.tsx").read_text(encoding="utf-8")
    conversation_page = (
        ROOT_DIR / "apps/web/app/studio/bots/[botId]/versions/[versionId]/conversations/page.tsx"
    ).read_text(encoding="utf-8")
    flow_page = (
        ROOT_DIR / "apps/web/app/studio/bots/[botId]/versions/[versionId]/flows/page.tsx"
    ).read_text(encoding="utf-8")

    assert "STUDIO_PAGE_CATALOGS[language]" in page_shell
    assert "getStudioPageLabel(studioCopy, title)" in page_shell
    assert "getStudioPageLabel(studioCopy, description)" in page_shell
    assert "export function StudioPageText" in table_page
    assert "<StudioPageText>보기</StudioPageText>" in conversation_page
    assert "<StudioPageText>대화 설계</StudioPageText>" in flow_page
def test_studio_page_native_catalog_covers_every_korean_source_label() -> None:
    catalog_path = ROOT_DIR / "apps/web/lib/i18n/studio-pages-complete-native.ts"
    assert catalog_path.is_file()

    catalog_source = catalog_path.read_text(encoding="utf-8")
    studio_source = (ROOT_DIR / "apps/web/lib/i18n/studio-pages.ts").read_text(encoding="utf-8")
    direct_korean_labels = set(re.findall(r'"([^"]*[가-힣][^"]*)"\s*:', studio_source))
    assert len(direct_korean_labels) >= 200

    baseline_keys: set[str] | None = None
    for language in ("zh-CN", "ja", "vi", "fr", "de"):
        marker = f'  "{language}": {{'
        assert marker in catalog_source
        block = catalog_source.split(marker, 1)[1].split("\n  },", 1)[0]
        translated = {
            json.loads(key): json.loads(value)
            for key, value in re.findall(
                r'^\s*("(?:[^"\\]|\\.)*")\s*:\s*("(?:[^"\\]|\\.)*")',
                block,
                re.MULTILINE,
            )
        }
        assert len(translated) >= 365, language
        assert direct_korean_labels <= translated.keys(), language
        assert all(value.strip() and not re.search(r"[가-힣]", value) for value in translated.values()), language
        if baseline_keys is None:
            baseline_keys = set(translated)
        else:
            assert set(translated) == baseline_keys, language

    assert "STUDIO_PAGE_COMPLETE_NATIVE" in studio_source
    assert '...STUDIO_PAGE_COMPLETE_NATIVE["zh-CN"]' in studio_source


def test_interactive_studio_messages_do_not_bypass_locale_catalogs() -> None:
    """Interactive notices, confirmation prompts, and accessibility text must be localized."""

    component_names = (
        "blocklist-settings-page.tsx", "bot-delete-page.tsx", "bot-hub-composition.tsx",
        "bot-hub-create-form.tsx", "bot-hub-home.tsx", "bot-hub-retraining-page.tsx",
        "bot-hub-settings.tsx", "botstation-settings-page.tsx", "conversation-default-settings-page.tsx",
        "conversation-message-settings-page.tsx", "flow-designer-page.tsx", "intent-start-page.tsx",
        "messenger-floating-buttons-page.tsx", "messenger-recommended-intents-page.tsx", "messenger-settings-page.tsx", "rule-settings-page.tsx",
        "simulator-page.tsx", "smalltalk-settings-page.tsx", "studio-workspace-provider.tsx",
    )
    direct_message = re.compile(
        r'(?:set(?:ErrorMessage|Message|Notice|Feedback|Toast|Banner|ResultMessage)|throw new Error|window\.(?:alert|confirm|prompt))'
        r'[^\n]*(?:"[^"\n]*[가-힣][^"\n]*"|`[^`\n]*[가-힣][^`\n]*`)'
    )
    direct_accessibility = re.compile(
        r'(?:alt|title|aria-label|data-help|placeholder)='
        r'(?:"[^"]*[가-힣][^"]*"|\{`[^`]*[가-힣][^`]*`\})'
    )
    violations: list[str] = []

    for name in component_names:
        source = (ROOT_DIR / "apps" / "web" / "components" / name).read_text(encoding="utf-8")
        for line_number, line in enumerate(source.splitlines(), start=1):
            if "i18n-allow-data" in line or "i18n-allow-contract" in line:
                continue
            translated = any(token in line for token in (
                "getStudioPageLabel(", "getIntentStartLabel(", "getFlowDesignerLabel(",
                "getSimulatorLabel(", "getStudioRuntimeMessage(", "copy.", "inputCopy.",
            ))
            if not translated and (direct_message.search(line) or direct_accessibility.search(line)):
                violations.append(f"{name}:{line_number}:{line.strip()}")

    assert not violations, "Unlocalized interactive copy remains:\n" + "\n".join(violations)

def test_studio_runtime_message_catalog_has_complete_native_translations() -> None:
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/studio-runtime-native.ts").read_text(encoding="utf-8")
    component_source = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT_DIR / "apps/web/components").glob("*.tsx")
    )
    used_keys = {
        json.loads(f'"{value}"')
        for value in re.findall(
            r'(?:getStudioRuntimeMessage|formatStudioRuntimeMessage)\([^,]+,\s*"((?:[^"\\]|\\.)*)"',
            component_source,
        )
    }
    assert len(used_keys) >= 70

    baseline_keys: set[str] | None = None
    for language in ("en", "zh-CN", "ja", "vi", "fr", "de"):
        marker = f'  "{language}": {{'
        assert marker in catalog_source
        block = catalog_source.split(marker, 1)[1].split("\n  },", 1)[0]
        translated = {
            json.loads(key): json.loads(value)
            for key, value in re.findall(
                r'^\s*("(?:[^"\\]|\\.)*")\s*:\s*("(?:[^"\\]|\\.)*")',
                block,
                re.MULTILINE,
            )
        }
        missing_keys = sorted(used_keys - translated.keys())
        assert not missing_keys, f"{language}: missing {len(missing_keys)} keys: {missing_keys}"
        assert all(value.strip() and not re.search(r"[가-힣]", value) for value in translated.values()), language
        if baseline_keys is None:
            baseline_keys = set(translated)
        else:
            assert set(translated) == baseline_keys, language

    assert 'DELETE' in catalog_source
    assert '`$_`' in catalog_source


def test_dynamic_studio_copy_does_not_fall_back_to_korean() -> None:
    """Dynamic labels and generated defaults must honor the selected UI or bot language."""

    forbidden_by_component = {
        "analysis-page.tsx": ('padStart(2, "0")}일`',),
        "flow-designer-page.tsx": (
            "정의되지 않은 변수 '$${root}'를 사용하고 있습니다.",
            "`TTS 테스트 URL: ${",
            "label: `조건 ${regularIndex}`",
        ),
        "rule-settings-page.tsx": (
            "`정규식 문법 오류: ${regexResult}`",
            '`${matchedRule.target || "의도/모듈 미연결"} 으로 연결됩니다.`',
            ': "룰이 매칭되지 않는 표현입니다.";',
        ),
        "intent-configure-page.tsx": (
            "cluster.name || `RAG 의도 ${index + 1}`",
            "cluster.name || `의도 ${index + 1}`",
            "makeDefaultAnswer(cluster.name || `의도 ${index + 1}`)",
        ),
        "version-management-page.tsx": ('`${selectedVersion.name} 복사본`',),
        "simulator-page.tsx": (
            '`항목 ${index + 1}`', '`주소 ${itemIndex + 1}`', '`${year}년 ${month + 1}월`',
            '`${fallback} 값을 확인해 주세요.`', '`${fallback}은(는) 필수입니다.`',
            '`탭 ${tabIndex + 1}`', '`${type || "UNKNOWN"} 컴포넌트`',
            'first || "Card 메시지입니다."', 'baseMessages[0] || "선택하세요."',
            'baseMessages[0] || "링크 버튼 메시지입니다."', 'first || "Carousel 메시지입니다."',
            'baseMessages[0] || "번호를 입력하세요."',
        ),
    }
    violations: list[str] = []
    component_dir = ROOT_DIR / "apps" / "web" / "components"
    for name, snippets in forbidden_by_component.items():
        source = (component_dir / name).read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet in source:
                violations.append(f"{name}: {snippet}")

    assert not violations, "Dynamic Korean copy remains:\n" + "\n".join(violations)


def test_simulator_separates_bot_language_from_analysis_language() -> None:
    source = (ROOT_DIR / "apps/web/components/simulator-page.tsx").read_text(encoding="utf-8")
    bot_language_leaks = (
        'getStudioRuntimeMessage(uiLanguage, "원하는 의도 없음")',
        'getStudioRuntimeMessage(uiLanguage, "다시 질문해주시면 다른 의도를 찾겠습니다.")',
        'getStudioRuntimeMessage(uiLanguage, "목록에 있는 버튼 중 하나를 선택해주세요.")',
        'makeMessage("system", "다음 대화 카드가 연결되어 있지 않습니다.")',
    )
    analysis_language_leaks = (
        '{log.order}. {log.cardType}',
        '[{log.utterance}] {log.description}',
        '{snapshot.order}. [{snapshot.utterance}] {snapshot.label}',
        '<summary>{snapshot.label}</summary>',
        '{["일", "월", "화", "수", "목", "금", "토"].map',
        'value || "시간 선택"', 'title || "토글"', 'title || description || "이미지"',
        'title || "동영상"', 'title || cleanRichFormText(text) || "확인"',
        '["title", "label", "name", "key"], "입력값"',
    )
    violations = [snippet for snippet in (*bot_language_leaks, *analysis_language_leaks) if snippet in source]
    assert not violations, "Simulator language-boundary leaks remain:\n" + "\n".join(violations)


def test_simulator_native_controls_and_timestamps_follow_ui_language() -> None:
    """Simulator chrome must not fall back to English or a fixed Korean time locale."""

    component_source = (ROOT_DIR / "apps/web/components/simulator-page.tsx").read_text(encoding="utf-8")
    catalog_source = (ROOT_DIR / "apps/web/lib/i18n/simulator.ts").read_text(encoding="utf-8")

    assert 'toLocaleTimeString("ko-KR"' not in component_source
    assert "SIMULATOR_TIME_LOCALES" in component_source
    assert component_source.count("formatMessageTime(message.timestamp, uiLanguage)") == 2

    assert "type SimulatorUiLabelKey = keyof typeof enUiLabels" in catalog_source
    assert "const simulatorNativeLabels" in catalog_source
    assert (
        'satisfies Record<Exclude<SupportedLanguage, "ko" | "en">, '
        "Record<SimulatorUiLabelKey, string>>"
    ) in catalog_source

    ui_label_block = catalog_source.split("const simulatorUiLabels", 1)[1].split(
        "export function getSimulatorLabel", 1
    )[0]
    assert "...enUiLabels" not in ui_label_block
    for language in ('"zh-CN"', "ja", "vi", "fr", "de"):
        assert f"{language}: simulatorNativeLabels" in ui_label_block
