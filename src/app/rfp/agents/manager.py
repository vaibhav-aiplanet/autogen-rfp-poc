import asyncio
import re
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from autogen_core import MessageContext, RoutedAgent, TopicId, message_handler
from pydantic import BaseModel, Field

from app.rfp.agents.extractor import ExtractedMessage, ExtractMessage
from app.rfp.agents.parser import ParsedMessage
from app.rfp.agents.section_generator import (GeneratedMessage,
                                              GenerateMessage, SectionData)
from app.rfp.services.file import FileProcessing
from app.rfp.utils import Topics

file_pattern = re.compile(r"(.*/)?(.*)\.(.*)")


class StartMessage(BaseModel):
    question_file_path: str


class Results(BaseModel):
    requirements: str | None = Field(default=None)
    expectations: str | None = Field(default=None)
    problem_statement: str | None = Field(default=None)
    sections: list[SectionData] | None = Field(default=None)


class ManagerAgent(RoutedAgent):

    def __init__(self, description: str):
        super().__init__(description)

        self.file_service = FileProcessing()
        self.extracted_results: ExtractedMessage | None = None

        self.bytes_content: bytes
        self.text_content: str
        self.file_name: str
        self.file_extension: str

        self.results = Results()

    @message_handler
    async def start(self, message: StartMessage, ctx: MessageContext) -> None:
        """
        Start the flow
        """

        rfp_id = uuid.uuid4().hex

        # TODO: Upload to S3

        match = file_pattern.match(message.question_file_path)
        if not match:
            raise Exception("Invalid file path")

        self.file_name = match.group(2)
        self.file_extention = match.group(3)

        self.bytes_content = self.file_service.read_file(message.question_file_path)
        self.text_content = self.file_service.bytesToText(self.bytes_content)

        chunks = self.file_service.split_text_into_chunks(self.text_content)

        # start both the processes
        await self.publish_message(
            ExtractMessage(chunks=chunks),
            TopicId(Topics.EXTRACT.value, rfp_id),
            cancellation_token=ctx.cancellation_token,
        )

        await self.publish_message(
            GenerateMessage(content=self.text_content),
            TopicId(Topics.GENERATE.value, rfp_id),
            cancellation_token=ctx.cancellation_token,
        )

    @message_handler
    async def extracted_handler(
        self, message: ExtractedMessage, ctx: MessageContext
    ) -> None:
        """
        After extracting info
        """

        print("Info extracted")
        self.extracted_results = message

        self.results.requirements = message.requirements
        self.results.expectations = message.expectations
        self.results.problem_statement = message.problem_statement

        if self.results.sections:
            print("Publishing results")
            await self.publish_message(
                self.results,
                TopicId("results", ctx.topic_id.source),
                cancellation_token=ctx.cancellation_token,
            )

        # TODO: save the results to db

    @message_handler
    async def generated_handler(
        self, message: GeneratedMessage, ctx: MessageContext
    ) -> None:
        """
        After generating sections
        """

        self.results.sections = message.sections
        print("Sections generated")

        if self.results.requirements:
            print("Publishing results")
            await self.publish_message(
                self.results,
                TopicId("results", ctx.topic_id.source),
                cancellation_token=ctx.cancellation_token,
            )
