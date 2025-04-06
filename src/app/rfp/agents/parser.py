from autogen_core import MessageContext, RoutedAgent, TopicId, message_handler
from pydantic import BaseModel

from app.rfp.services.file import FileProcessing
from app.rfp.utils import Topics


class ParserMessage(BaseModel):
    chunks: list[str]


class ParsedMessage(BaseModel):
    chunks: list[str]
    file_name: str
    file_type: str


class ParserAgent(RoutedAgent):

    @message_handler
    async def generate_sections(
        self, message: ParserMessage, ctx: MessageContext
    ) -> None:
        """
        Handler to parse question file
        """

        pdf_service = FileProcessing()
        with open(message.question_file_path, "rb") as f:
            content = f.read()
            content = pdf_service.bytesToText(content)
            chunks = pdf_service.split_text_recursively(content)

            assert ctx.topic_id is not None

            topic_id = TopicId(Topics.PARSED.value, ctx.topic_id.source)
            await self.publish_message(
                ParsedMessage(
                    file_name=message.question_file_path,
                    file_type="application/pdf",
                    chunks=chunks,
                ),
                topic_id,
                cancellation_token=ctx.cancellation_token,
            )
