from __future__ import annotations

from typing import Any, Mapping

SHEETS_SCOPES = ("https://www.googleapis.com/auth/spreadsheets",)


def create_gspread_client(service_account_info: Mapping[str, Any]):
    """Cria o mesmo cliente usado no projeto original, a partir do st.secrets."""
    import gspread
    from google.oauth2 import service_account

    info = dict(service_account_info or {})
    if not info:
        raise ValueError("As credenciais [gcp_service_account] não foram configuradas.")
    credentials = service_account.Credentials.from_service_account_info(
        info,
        scopes=list(SHEETS_SCOPES),
    )
    return gspread.authorize(credentials)


def open_spreadsheet(
    service_account_info: Mapping[str, Any],
    *,
    spreadsheet_url: str = "",
    spreadsheet_id: str = "",
):
    client = create_gspread_client(service_account_info)
    if spreadsheet_id.strip():
        return client.open_by_key(spreadsheet_id.strip())
    if spreadsheet_url.strip():
        return client.open_by_url(spreadsheet_url.strip())
    raise ValueError(
        "Informe private_gsheets_url, google_sheets.spreadsheet_url ou "
        "google_sheets.spreadsheet_id no secrets.toml."
    )
