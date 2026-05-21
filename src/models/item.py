import hashlib
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from utils.slug import slugify

class ScrapedItem(BaseModel):
    title: str
    description: Optional[str] = ""
    source: str
    source_url: str
    category: str
    content_type: Optional[str] = None
    institution: str
    institution_slug: Optional[str] = None
    posted_at: Optional[datetime] = None
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    tags: List[str] = Field(default_factory=list)
    slug: Optional[str] = None
    raw_html: Optional[str] = None
    scraper_name: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_official: bool = True
    merged_into_notice_id: Optional[int] = None
    content_hash: Optional[str] = None
    attachment_url: Optional[str] = None
    institution_id: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def populate_slugs(cls, data):
        if isinstance(data, dict):
            # Auto-generate institution_slug if missing
            inst = data.get("institution", "")
            if inst and not data.get("institution_slug"):
                data["institution_slug"] = slugify(inst)
            
            # Auto-generate unique slug if missing
            title = data.get("title", "")
            source_url = data.get("source_url", "")
            if title and source_url and not data.get("slug"):
                slug_base = f"{slugify(inst)}-{slugify(title)}"
                # Append short hash of source URL to avoid slug collisions
                url_hash = hashlib.md5(source_url.encode("utf-8")).hexdigest()[:8]
                # Truncate slug_base to 100 chars to avoid very long filenames/slugs
                data["slug"] = f"{slug_base[:100]}-{url_hash}"
                
            # Default content_type if missing (falls back to category)
            if not data.get("content_type") and data.get("category"):
                data["content_type"] = data.get("category")

            # Auto-populate is_official based on scraper name
            scr_name = data.get("scraper_name")
            if scr_name in ("assam_career", "daily_assam_job", "ncs_portal"):
                data["is_official"] = False
            else:
                data["is_official"] = True

            # Auto-generate content_hash if missing
            desc = data.get("description", "") or ""
            if title and not data.get("content_hash"):
                norm_title = " ".join(title.split()).strip().lower()
                norm_desc = " ".join(desc.split()).strip().lower()
                hash_base = f"{norm_title}|{norm_desc}"
                data["content_hash"] = hashlib.md5(hash_base.encode("utf-8")).hexdigest()
        return data

    def to_dict(self) -> dict:
        """
        Convert to dict format suitable for Supabase insertion,
        formatting datetime fields to string format.
        """
        data = self.model_dump()
        if data.get("posted_at") and isinstance(data["posted_at"], datetime):
            data["posted_at"] = data["posted_at"].isoformat()
        if isinstance(data.get("last_seen_at"), datetime):
            data["last_seen_at"] = data["last_seen_at"].isoformat()
        if isinstance(data.get("scraped_at"), datetime):
            data["scraped_at"] = data["scraped_at"].isoformat()
        return data
