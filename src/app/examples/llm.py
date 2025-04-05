from dataclasses import dataclass

import instructor
import openai
from autogen_core import (DefaultTopicId, MessageContext, RoutedAgent,
                          default_subscription, message_handler)
from pydantic import BaseModel


@dataclass
class Message:
    content: str


def get_llm(system_prompt: str):
    model = "qwen2.5-coder:14b"
    client = instructor.from_openai(
        openai.OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        ),
        mode=instructor.Mode.JSON,
    )

    def generate(response_model: type[BaseModel], prompt: str):
        try:
            message = dict(role="user", content=prompt)

            print("[GENERATE]: ", prompt)
            print("[GENERATE]: Generating...")
            response = client.create(
                response_model,
                [message],  # type:ignore
                model=model,
            )
            return response
        except KeyboardInterrupt:
            print("Quitting")
        except Exception as e:
            raise Exception(f"Failed to generate error: {str(e)}")

    return generate


@default_subscription
class MainAgent(RoutedAgent):

    system_prompt: str = (
        'You are a person in a group discussion. Give your responses as a first person. To stop the flow respond with "TERMINATE"'
    )

    @classmethod
    def factory(cls):
        return cls(cls.system_prompt)

    def __init__(self, system_prompt: str):
        super().__init__("Bob")
        self.system_prompt = system_prompt
        self.generate = get_llm(system_prompt)

    @message_handler
    async def handle_message(self, message: Message, _: MessageContext) -> None:

        class ResponseModel(BaseModel):
            response: str

        response: str = self.generate(ResponseModel, message.content).response
        if "TERMINATE" in response:
            return

        print(f"[{self.type}]: {response}")

        await self.publish_message(Message(content=response), DefaultTopicId())  # type: ignore


@default_subscription
class AnotherAgent(RoutedAgent):

    system_prompt: str = (
        'You are a person in a group discussion. Give your responses as a first person. To stop the flow respond with "TERMINATE"'
    )

    @classmethod
    def factory(cls):
        return cls(cls.system_prompt)

    def __init__(self, system_prompt: str):
        super().__init__("Bob")
        self.system_prompt = system_prompt
        self.generate = get_llm(system_prompt)

    @message_handler
    async def handle_message(self, message: Message, _: MessageContext) -> None:

        class ResponseModel(BaseModel):
            response: str

        response: str = self.generate(ResponseModel, message.content).response
        if "TERMINATE" in response:
            return

        print(f"[{self.type}]: {response}")

        await self.publish_message(Message(content=response), DefaultTopicId())  # type: ignore


async def main():
    from autogen_core import AgentId, SingleThreadedAgentRuntime

    runtime = SingleThreadedAgentRuntime()
    print("[INFO]: Created runtime")

    # register agents
    agent1 = await MainAgent.register(runtime, "Agent-1", MainAgent.factory)
    _ = await AnotherAgent.register(runtime, "Agent-2", AnotherAgent.factory)

    print("[INFO]: Registered agents")

    # Start the runtime and send a direct message to the checker.
    runtime.start()
    await runtime.send_message(
        Message(content="You have to lead the GD regarding AI in pharma. Lead it"),
        AgentId(agent1.type, "default"),
    )
    print("[INFO]: Message sent")

    await runtime.stop_when_idle()
