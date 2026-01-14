"""
Airtable API client for database operations
"""

import logging
from typing import Optional, Any
from pyairtable import Api, Table

from app.config import get_settings

logger = logging.getLogger(__name__)


class AirtableClient:
    """Client for Airtable API operations"""

    def __init__(self):
        settings = get_settings()
        self.api = Api(settings.airtable_pat)
        self.base_id = settings.airtable_base_id

        # Table references
        self.input_table_id = settings.airtable_input_table_id
        self.output_table_id = settings.airtable_output_table_id
        self.doubts_table_id = settings.airtable_doubts_table_id

    def _get_table(self, table_id: str) -> Table:
        """Get a table reference"""
        return self.api.table(self.base_id, table_id)

    # ==================== Input Table Operations ====================

    async def create_article_input(
        self,
        article_id: str,
        article_name: str,
        article_section: str,
        article_content: str,
        article_rating: Optional[str] = None,
        rating_justification: Optional[str] = None,
    ) -> dict:
        """
        Create a new article record in the Input table.

        Returns:
            Created record with ID
        """
        table = self._get_table(self.input_table_id)

        fields = {
            "article_id": article_id,
            "article_name": article_name,
            "article_section": article_section,
            "article_content_text": article_content,
            "status_auto": "Not Started",
        }

        if article_rating:
            fields["article_rating"] = article_rating
        if rating_justification:
            fields["article_rating_justification"] = rating_justification

        try:
            record = table.create(fields)
            logger.info(f"Created article input record: {record['id']}")
            return record
        except Exception as e:
            logger.error(f"Failed to create article input: {e}")
            raise

    async def update_article_input(
        self,
        record_id: str,
        fields: dict[str, Any],
    ) -> dict:
        """Update an article input record"""
        table = self._get_table(self.input_table_id)

        try:
            record = table.update(record_id, fields)
            logger.info(f"Updated article input record: {record_id}")
            return record
        except Exception as e:
            logger.error(f"Failed to update article input: {e}")
            raise

    async def get_article_input(self, record_id: str) -> dict:
        """Get an article input record by ID"""
        table = self._get_table(self.input_table_id)
        return table.get(record_id)

    async def search_article_input(
        self,
        article_id: Optional[str] = None,
        article_name: Optional[str] = None,
    ) -> list[dict]:
        """Search for article input records"""
        table = self._get_table(self.input_table_id)

        formula_parts = []
        if article_id:
            formula_parts.append(f"{{article_id}}='{article_id}'")
        if article_name:
            formula_parts.append(f"{{article_name}}='{article_name}'")

        formula = f"AND({','.join(formula_parts)})" if formula_parts else None

        return table.all(formula=formula)

    # ==================== Output Table Operations ====================

    async def create_image_output(
        self,
        article_id: str,
        article_name: str,
        image_name: str,
        image_link: str,
        placement: str,
        interim_link: Optional[str] = None,
        changes_text: Optional[str] = None,
    ) -> dict:
        """
        Create a new image record in the Output table.

        Returns:
            Created record with ID
        """
        table = self._get_table(self.output_table_id)

        fields = {
            "article_id": article_id,
            "article_name": article_name,
            "image_name": image_name,
            "image_link": image_link,
            "Placement": placement,
        }

        if interim_link:
            fields["interim-image-link"] = interim_link
        if changes_text:
            fields["changes_text"] = changes_text

        try:
            record = table.create(fields)
            logger.info(f"Created image output record: {record['id']}")
            return record
        except Exception as e:
            logger.error(f"Failed to create image output: {e}")
            raise

    async def update_image_output(
        self,
        record_id: str,
        fields: dict[str, Any],
    ) -> dict:
        """Update an image output record"""
        table = self._get_table(self.output_table_id)

        try:
            record = table.update(record_id, fields)
            logger.info(f"Updated image output record: {record_id}")
            return record
        except Exception as e:
            logger.error(f"Failed to update image output: {e}")
            raise

    async def search_image_outputs(
        self,
        article_id: str,
        article_name: Optional[str] = None,
        image_name: Optional[str] = None,
    ) -> list[dict]:
        """Search for image output records"""
        table = self._get_table(self.output_table_id)

        formula_parts = [f"{{article_id}}='{article_id}'"]
        if article_name:
            formula_parts.append(f"{{article_name}}='{article_name}'")
        if image_name:
            formula_parts.append(f"{{image_name}}='{image_name}'")

        formula = f"AND({','.join(formula_parts)})"

        return table.all(formula=formula, sort=["rowSequence"])

    # ==================== Doubts Table Operations ====================

    async def create_doubt_record(
        self,
        article_id: str,
        article_name: str,
        doubt_data: Optional[dict] = None,
    ) -> dict:
        """
        Create a new doubt record in the Doubts table.

        Returns:
            Created record with ID
        """
        table = self._get_table(self.doubts_table_id)

        fields = {
            "article_id": article_id,
            "article_name": article_name,
            "status": "Not Started",
        }

        if doubt_data:
            fields.update(doubt_data)

        try:
            record = table.create(fields)
            logger.info(f"Created doubt record: {record['id']}")
            return record
        except Exception as e:
            logger.error(f"Failed to create doubt record: {e}")
            raise

    async def update_doubt_record(
        self,
        record_id: str,
        fields: dict[str, Any],
    ) -> dict:
        """Update a doubt record"""
        table = self._get_table(self.doubts_table_id)

        try:
            record = table.update(record_id, fields)
            logger.info(f"Updated doubt record: {record_id}")
            return record
        except Exception as e:
            logger.error(f"Failed to update doubt record: {e}")
            raise

    async def search_doubt_records(
        self,
        article_id: str,
    ) -> list[dict]:
        """Search for doubt records by article ID"""
        table = self._get_table(self.doubts_table_id)

        formula = f"{{article_id}}='{article_id}'"

        return table.all(formula=formula)
