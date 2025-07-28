"""
Factory Boy factories for Attachment models.
"""

import uuid

import factory
from django.core.files.uploadedfile import SimpleUploadedFile
from factory.django import DjangoModelFactory

from apps.attachments.constants import AttachmentType
from apps.attachments.models import Attachment
from tests.factories.entry_factories import EntryFactory


class AttachmentFactory(DjangoModelFactory):
    """Factory for creating Attachment instances."""

    class Meta:
        model = Attachment

    attachment_id = factory.LazyFunction(uuid.uuid4)
    entry = factory.SubFactory(EntryFactory)
    file_type = factory.Iterator([choice[0] for choice in AttachmentType.choices])

    @factory.lazy_attribute
    def file_url(self):
        """Generate a file based on the file_type."""
        if self.file_type == AttachmentType.IMAGE:
            return SimpleUploadedFile(
                name="test_image.jpg",
                content=b"fake image content",
                content_type="image/jpeg",
            )
        elif self.file_type == AttachmentType.PDF:
            return SimpleUploadedFile(
                name="test_document.pdf",
                content=b"fake pdf content",
                content_type="application/pdf",
            )
        elif self.file_type == AttachmentType.SPREADSHEET:
            return SimpleUploadedFile(
                name="test_spreadsheet.xlsx",
                content=b"fake spreadsheet content",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            return SimpleUploadedFile(
                name="test_file.txt",
                content=b"fake file content",
                content_type="text/plain",
            )


class ImageAttachmentFactory(AttachmentFactory):
    """Factory for creating image attachments."""

    file_type = AttachmentType.IMAGE
    file_url = factory.LazyAttribute(
        lambda obj: SimpleUploadedFile(
            name="test_image.jpg",
            content=b"fake image content",
            content_type="image/jpeg",
        )
    )


class PDFAttachmentFactory(AttachmentFactory):
    """Factory for creating PDF attachments."""

    file_type = AttachmentType.PDF
    file_url = factory.LazyAttribute(
        lambda obj: SimpleUploadedFile(
            name="test_document.pdf",
            content=b"fake pdf content",
            content_type="application/pdf",
        )
    )


class SpreadsheetAttachmentFactory(AttachmentFactory):
    """Factory for creating spreadsheet attachments."""

    file_type = AttachmentType.SPREADSHEET
    file_url = factory.LazyAttribute(
        lambda obj: SimpleUploadedFile(
            name="test_spreadsheet.xlsx",
            content=b"fake spreadsheet content",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    )


class OtherAttachmentFactory(AttachmentFactory):
    """Factory for creating other type attachments."""

    file_type = AttachmentType.OTHER
    file_url = factory.LazyAttribute(
        lambda obj: SimpleUploadedFile(
            name="test_file.txt",
            content=b"fake text content",
            content_type="text/plain",
        )
    )


class AttachmentWithEntryFactory(AttachmentFactory):
    """Factory for creating attachments with specific entry relationships."""

    @factory.post_generation
    def with_entry_details(self, create, extracted, **kwargs):
        """Add specific entry details if needed."""
        if not create:
            return

        if extracted:
            # Allow customization of the entry
            for key, value in extracted.items():
                setattr(self.entry, key, value)
            self.entry.save()


class MultipleAttachmentsFactory(factory.Factory):
    """Factory for creating multiple attachments for a single entry."""

    class Meta:
        model = list

    @classmethod
    def create(cls, **kwargs):
        """Create multiple attachments for a single entry."""
        entry = kwargs.get("entry") or EntryFactory()
        count = kwargs.get("count", 3)

        attachments = []
        for i in range(count):
            attachment = AttachmentFactory(entry=entry)
            attachments.append(attachment)

        return attachments
