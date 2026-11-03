"use client";

import { ChangeEvent, type CSSProperties, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AdminInteractiveTablePage } from "@/components/admin-interactive-table-page";
import { useI18n } from "@/components/language-provider";
import { applyAdminLicense, fetchAdminLicense, type AdminLicenseStatusResponse } from "@/lib/admin-api";
import { loadAuthSession } from "@/lib/auth";
import { ADMIN_LICENSE_CATALOGS, formatAdminLicenseText, type AdminLicenseCatalog } from "@/lib/i18n/admin-license";
import { SUPPORTED_LANGUAGES } from "@/lib/language";

function displayNumber(value: number | null, locale: string) {
  return value === null ? "-" : value.toLocaleString(locale);
}

function licenseStatusText(status: string | undefined, copy: AdminLicenseCatalog) {
  if (status === "active") return copy.active;
  if (status === "expired") return copy.expired;
  if (status === "replaced") return copy.replaced;
  return status || "-";
}

export default function AdminLicensePage() {
  const { language: uiLanguage } = useI18n();
  const copy = ADMIN_LICENSE_CATALOGS[uiLanguage];
  const locale = SUPPORTED_LANGUAGES.find((item) => item.code === uiLanguage)?.intlLocale ?? "ko-KR";
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [licenseStatus, setLicenseStatus] = useState<AdminLicenseStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [message, setMessage] = useState("");

  const loadLicense = useCallback(async () => {
    const session = loadAuthSession();
    if (!session) return;
    setLoading(true);
    try {
      const data = await fetchAdminLicense(session.access_token);
      setLicenseStatus(data);
      setMessage(data.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : copy.loadFailed);
    } finally {
      setLoading(false);
    }
  }, [copy.loadFailed]);

  useEffect(() => {
    void loadLicense();
  }, [loadLicense]);

  async function handleLicenseFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const session = loadAuthSession();
    if (!session) return;

    setApplying(true);
    try {
      const licenseText = await file.text();
      const data = await applyAdminLicense(session.access_token, licenseText);
      setLicenseStatus(data);
      setMessage(copy.applied);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : copy.applyFailed);
    } finally {
      setApplying(false);
    }
  }

  const rows = useMemo(
    () =>
      (licenseStatus?.usage ?? []).map((item) => ({
        key: item.key,
        cells: [
          item.key === "bots" ? copy.perUserBots : item.label,
          displayNumber(item.limit, locale),
          displayNumber(item.used, locale),
          displayNumber(item.remaining, locale),
          item.expires_at ?? "-",
        ],
      })),
    [licenseStatus, locale, copy],
  );

  const currentLicense = licenseStatus?.license;
  const toolbarRight = (
    <span className="admin-page__selection">
      {loading ? copy.loading : message || "-"}
    </span>
  );

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".license,application/json"
        onChange={handleLicenseFile}
        style={{ display: "none" }}
      />
      <AdminInteractiveTablePage
        title={copy.title}
        searchPlaceholder={copy.searchPlaceholder}
        totalText={formatAdminLicenseText(copy.total, { count: rows.length })}
        columns={[copy.category, copy.limit, copy.used, copy.remaining, copy.expiresAt]}
        rows={rows}
        template="minmax(120px, 0.9fr) minmax(120px, 1fr) minmax(120px, 1fr) minmax(120px, 1fr) minmax(140px, 1fr)"
        topRight={
          <button
            type="button"
            className="admin-page__primary"
            disabled={applying}
            onClick={() => fileInputRef.current?.click()}
          >
            {applying ? copy.applying : copy.upload}
          </button>
        }
        toolbarRight={toolbarRight}
        loading={loading}
      />

      <p className="admin-page__description">{copy.perUserBotsHelp}</p>
      <section className="admin-page admin-license-summary" aria-label={copy.licenseDetails}>
        <h2>{copy.licenseInfo}</h2>
        <div className="data-grid data-grid--admin" style={{ "--data-grid-template": "1fr 1fr 1fr 1fr" } as CSSProperties}>
          <div className="data-grid__row data-grid__row--header">
            <div className="data-grid__cell">{copy.licenseId}</div>
            <div className="data-grid__cell">{copy.customer}</div>
            <div className="data-grid__cell">{copy.status}</div>
            <div className="data-grid__cell">{copy.issuedAt}</div>
          </div>
          <div className="data-grid__row">
            <div className="data-grid__cell">{currentLicense?.license_id ?? "-"}</div>
            <div className="data-grid__cell">{currentLicense?.customer_name ?? "-"}</div>
            <div className="data-grid__cell">{licenseStatusText(currentLicense?.status, copy)}</div>
            <div className="data-grid__cell">{currentLicense?.issued_at ?? "-"}</div>
          </div>
        </div>
      </section>
    </>
  );
}
