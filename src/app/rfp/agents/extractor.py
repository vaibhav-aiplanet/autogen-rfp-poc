import json

from autogen_core import MessageContext, RoutedAgent, TopicId, message_handler
from autogen_core.models import SystemMessage, UserMessage
from pydantic import BaseModel

from app.core.llm import get_llm_client
from app.rfp.utils import Topics


class ExtractMessage(BaseModel):
    chunks: list[str]


class ExtractedMessage(BaseModel):
    requirements: str
    problem_statement: str
    expectations: str


class ExtractorAgent(RoutedAgent):

    def __init__(self, description: str):
        super().__init__(description)

        self.llm_client = get_llm_client()

        self.system_prompt = f"""
      You are a specialized text classifier that categorizes statements into three categories: problem_statement, requirements, and expectations. You will process batches of text lists and provide clear classification with justification in JSON format.

      TASK:
      1. Analyze each list of text provided in a batch
      2. Classify each text item into one of three categories:
         - problem_statement: Statements that describe issues, challenges, or situations that need to be addressed
         - requirements: Statements that outline specific needs, specifications, or necessary conditions
         - expectations: Statements that describe desired outcomes, goals, or anticipated results
      3. Provide your classifications in JSON format with justifications for each category
      4. Maintain context between batches by incorporating previous classifications into your analysis

      CLASSIFICATION GUIDELINES:
      - problem_statement: Look for phrases describing current issues, pain points, challenges, or questions that need answering
      - requirements: Look for phrases describing what must/should be done, necessary features, or essential conditions
      - expectations: Look for phrases describing desired outcomes, goals, targets, or what someone hopes to achieve

       1. Return ONLY a valid JSON object with EXACTLY this structure:
      {{
          "problem_statement": "Summarized problem statements text here",
          "requirements": "Summarized requirements text here",
          "expectations": "Summarized expectations text here"
      }}
      
      2. DO NOT include:
         - Any text before the JSON (like "Here's the classification:")
         - Any text after the JSON (like "I hope this helps")
         - Any markdown formatting for the JSON itself (no backticks)
         - Any explanations about your process
         - Any nested objects inside these three fields
         - Any arrays instead of strings for these fields
      
      3. Each of the three fields must contain only a STRING with:
         - A coherent summary paragraph that synthesizes all relevant texts
         - Both previous insights and new information in a cohesive way
         - Brief justification for the classification
      
      4. Make sure your JSON is properly formatted with:
         - Double quotes for all keys and string values
         - No trailing commas
         - No additional fields beyond the three specified ones
      
      START YOUR RESPONSE WITH THE OPENING BRACE {{, AND END WITH THE CLOSING BRACE }}. DO NOT INCLUDE ANYTHING ELSE.
    """

        self.user_prompt = """
      PREVIOUS CLASSIFICATION:
      {previous_response}

      Consider the previous classification above when analyzing the new batch of texts. Add to or modify the previous classifications as needed based on the new information.

      BATCH OF TEXT:
      {chunks}

      IMPORTANT: Your response must be ONLY valid JSON without any markdown formatting, code block markers, or additional text.

      OUTPUT FORMAT:
      {{
          "problem_statement": "Summarize all texts classified as problem statements. Include a consolidated summary of the key problems identified, along with a brief justification for why they are considered problems.",
          "requirements": "Summarize all texts classified as requirements. Include a consolidated summary of the key requirements identified, along with a brief justification for why they are considered requirements.",
          "expectations": "Summarize all texts classified as expectations. Include a consolidated summary of the key expectations identified, along with a brief justification for why they are considered expectations."
      }}

      For each category, provide a coherent summary paragraph that synthesizes all the relevant texts. Ensure your response includes both previous insights and new information in a cohesive way.
    """

    @message_handler
    async def extract_info(self, message: ExtractMessage, ctx: MessageContext) -> None:
        """
        Handler to extract
            - **Problem Statement**
            - **Requirements**
            - **Expectations**
        """

        print("Extracting")
        assert ctx.topic_id is not None

        # read the file
        chunks = message.chunks

        # get the response by chunking
        previous_responses = ""
        batch_size = 300
        batches: list[list[str]] = []
        batch: list[str] = []
        for i in range(len(chunks)):
            batch.append(chunks[i])
            if len(batch) == batch_size:
                batches.append(batch)
                batch = []
        if batch:
            batches.append(batch)

        for i in batches:
            prompt = self.user_prompt.format(
                previous_response=previous_responses, chunks=i
            )

            response = await self.llm_client.create(
                [
                    SystemMessage(content=self.system_prompt),
                    UserMessage(content=prompt, source="User"),
                ]
            )

            assert isinstance(response.content, str)
            previous_responses = response.content

        data = json.loads(previous_responses)

        # send the data to manager agent
        topic_id = TopicId(Topics.EXTRACTED.value, ctx.topic_id.source)
        await self.publish_message(
            ExtractedMessage(
                requirements=data.get("requirements"),
                problem_statement=data.get("problem_statement"),
                expectations=data.get("expectations"),
            ),
            topic_id,
            cancellation_token=ctx.cancellation_token,
        )
        print("Published the info")
