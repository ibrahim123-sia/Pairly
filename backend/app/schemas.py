from typing import List, Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    contact_email: Optional[str] = None
    brand_primary_color: Optional[str] = None
    theme_mode: Optional[str] = None


class ScheduledJobUpsertRequest(BaseModel):
    is_enabled: Optional[bool] = False
    cron_expression: Optional[str] = "0 2 * * *"
    email_summary_to: Optional[str] = None


class CreateStoreRequest(BaseModel):
    name: str
    manager_email: str
    manager_name: Optional[str] = None
    manager_full_name: Optional[str] = None
    description: Optional[str] = None
    contact_email: Optional[str] = None
    theme_mode: Optional[str] = "light"
    brand_primary_color: Optional[str] = None
    slug: Optional[str] = None


class DisableStoreRequest(BaseModel):
    reason: Optional[str] = None


class PDFExportRequest(BaseModel):
    sections: Optional[List[str]] = ["summary", "top_rules", "top_products"]
