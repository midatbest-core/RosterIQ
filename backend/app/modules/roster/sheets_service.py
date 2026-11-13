from __future__ import annotations

import json
import logging
import os
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)

GOOGLE_SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def is_google_sheets_configured() -> bool:
    """Checks whether server-side Google Sheets OAuth or Service Account credentials exist."""
    settings = get_settings()
    if settings.google_sheets_enabled:
        return True
    if settings.google_service_account_info or settings.google_service_account_file:
        return True
    if settings.google_client_id and settings.google_client_secret:
        return True
    return False


def get_google_sheets_status() -> dict[str, Any]:
    """Returns the current readiness and configuration status of Google Sheets integration."""
    settings = get_settings()
    configured = is_google_sheets_configured()
    return {
        "enabled": configured,
        "client_id_configured": bool(settings.google_client_id),
        "service_account_configured": bool(
            settings.google_service_account_info or settings.google_service_account_file
        ),
        "scopes": GOOGLE_SHEETS_SCOPES,
        "message": (
            "Google Sheets export is ready."
            if configured
            else "Google Sheets export is unconfigured on the server. Configure ROSTERIQ_GOOGLE_CLIENT_ID or service account."
        ),
    }


def resolve_google_credentials(access_token: str | None = None) -> Any:
    """Resolves google.oauth2 credentials from user token or server-side service account."""
    settings = get_settings()

    # 1. User-provided OAuth 2.0 access token (from client auth flow)
    if access_token:
        try:
            from google.oauth2.credentials import Credentials

            return Credentials(token=access_token, scopes=GOOGLE_SHEETS_SCOPES)
        except Exception as e:
            logger.error("Failed to initialize Google user credentials: %s", e)
            raise AppError("INVALID_GOOGLE_TOKEN", "Invalid or malformed Google access token.", 401) from e

    # 2. Server-side Service Account info JSON string
    if settings.google_service_account_info:
        try:
            from google.oauth2.service_account import Credentials as SACredentials

            info = json.loads(settings.google_service_account_info)
            return SACredentials.from_service_account_info(info, scopes=GOOGLE_SHEETS_SCOPES)
        except Exception as e:
            logger.error("Failed to parse ROSTERIQ_GOOGLE_SERVICE_ACCOUNT_INFO: %s", e)
            raise AppError("GOOGLE_CONFIG_ERROR", "Invalid Google service account configuration.", 500) from e

    # 3. Server-side Service Account JSON file path
    if settings.google_service_account_file and os.path.exists(settings.google_service_account_file):
        try:
            from google.oauth2.service_account import Credentials as SACredentials

            return SACredentials.from_service_account_file(
                settings.google_service_account_file, scopes=GOOGLE_SHEETS_SCOPES
            )
        except Exception as e:
            logger.error("Failed to load ROSTERIQ_GOOGLE_SERVICE_ACCOUNT_FILE: %s", e)
            raise AppError("GOOGLE_CONFIG_ERROR", "Failed to load Google service account file.", 500) from e

    # Not configured
    raise AppError(
        "GOOGLE_SHEETS_NOT_CONFIGURED",
        "Google Sheets export is not configured on this server. Please use direct CSV export or configure Google OAuth.",
        400,
    )


def build_sheets_client(credentials: Any) -> Any:
    """Constructs the official Google Sheets API v4 Resource."""
    try:
        from googleapiclient.discovery import build

        return build("sheets", "v4", credentials=credentials, cache_discovery=False)
    except Exception as e:
        logger.error("Failed to build Google Sheets client: %s", e)
        raise AppError("GOOGLE_API_ERROR", f"Failed to initialize Google Sheets service: {e}", 502) from e


def create_and_format_roster_sheet(
    credentials: Any,
    spreadsheet_title: str,
    fieldnames: list[str],
    rows_data: list[dict[str, str]],
) -> dict[str, Any]:
    """Creates a new Google Spreadsheet, populates roster records, and formats headers/columns."""
    from googleapiclient.errors import HttpError

    try:
        service = build_sheets_client(credentials)

        # 1. Create Spreadsheet
        create_body = {
            "properties": {
                "title": spreadsheet_title,
                "locale": "en_US",
            },
            "sheets": [
                {
                    "properties": {
                        "sheetId": 0,
                        "title": "Roster Schedule",
                        "gridProperties": {
                            "frozenRowCount": 1,
                        },
                    }
                }
            ],
        }
        create_resp = service.spreadsheets().create(body=create_body).execute()
        spreadsheet_id = create_resp["spreadsheetId"]
        spreadsheet_url = create_resp.get(
            "spreadsheetUrl", f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        )

        # 2. Populate Values
        values: list[list[str]] = [fieldnames]
        for row in rows_data:
            values.append([str(row.get(f, "-")) for f in fieldnames])

        value_body = {"values": values}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="A1",
            valueInputOption="USER_ENTERED",
            body=value_body,
        ).execute()

        # 3. Format Headers & Table Styling
        num_cols = len(fieldnames)
        requests = [
            # Header Row Style: Navy background, White bold text, Center aligned
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": num_cols,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.12, "green": 0.16, "blue": 0.23},  # #1E293B
                            "textFormat": {
                                "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                                "bold": True,
                                "fontSize": 10,
                            },
                            "horizontalAlignment": "CENTER",
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
                }
            },
            # Auto-resize columns
            {
                "autoResizeDimensions": {
                    "dimensions": {
                        "sheetId": 0,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": num_cols,
                    }
                }
            },
        ]

        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body={"requests": requests}
        ).execute()

        return {
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_url": spreadsheet_url,
            "title": spreadsheet_title,
            "rows_exported": len(rows_data),
        }

    except HttpError as err:
        logger.error("Google Sheets API HttpError: %s (status: %s)", err, err.resp.status)
        if err.resp.status == 401:
            raise AppError(
                "GOOGLE_AUTH_EXPIRED",
                "Google authorization has expired or was revoked. Please reconnect your Google account.",
                401,
            ) from err
        if err.resp.status == 403:
            raise AppError(
                "GOOGLE_QUOTA_OR_PERMISSION_DENIED",
                "Google API quota exceeded or permission denied. Verify Google Cloud project quotas.",
                403,
            ) from err
        raise AppError(
            "GOOGLE_API_ERROR",
            f"Google Sheets API error: {err.reason if hasattr(err, 'reason') else err}",
            502,
        ) from err
    except AppError:
        raise
    except Exception as e:
        logger.error("Unexpected error during Google Sheets export: %s", e)
        raise AppError("GOOGLE_EXPORT_FAILED", f"Failed to export to Google Sheets: {e}", 500) from e

