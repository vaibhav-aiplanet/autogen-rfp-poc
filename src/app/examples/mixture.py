import asyncio
from dataclasses import dataclass
from typing import List

from autogen_core import (AgentId, MessageContext, RoutedAgent,
                          SingleThreadedAgentRuntime, message_handler)
from autogen_core.models import (ChatCompletionClient, SystemMessage,
                                 UserMessage)

from app.llm import get_llm_client


@dataclass
class WorkerTask:
    task: str
    previous_results: List[str]


@dataclass
class WorkerTaskResult:
    result: str


@dataclass
class UserTask:
    task: str


@dataclass
class FinalResult:
    result: str


class WorkerAgent(RoutedAgent):
    def __init__(
        self,
        model_client: ChatCompletionClient,
    ) -> None:
        super().__init__(description="Worker Agent")
        self._model_client = model_client

    @message_handler
    async def handle_task(
        self, message: WorkerTask, ctx: MessageContext
    ) -> WorkerTaskResult:
        if message.previous_results:
            # If previous results are provided, we need to synthesize them to create a single prompt.
            system_prompt = "You have been provided with a set of responses from various open-source models to the latest user query. Your task is to synthesize these responses into a single, high-quality response. It is crucial to critically evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect. Your response should not simply replicate the given answers but should offer a refined, accurate, and comprehensive reply to the instruction. Ensure your response is well-structured, coherent, and adheres to the highest standards of accuracy and reliability.\n\nResponses from models:"
            system_prompt += "\n" + "\n\n".join(
                [f"{i+1}. {r}" for i, r in enumerate(message.previous_results)]
            )
            model_result = await self._model_client.create(
                [
                    SystemMessage(content=system_prompt),
                    UserMessage(content=message.task, source="user"),
                ]
            )
        else:
            # If no previous results are provided, we can simply pass the user query to the model.
            model_result = await self._model_client.create(
                [UserMessage(content=message.task, source="user")]
            )
        assert isinstance(model_result.content, str)
        print(f"{'-'*80}\nWorker-{self.id}:\n{model_result.content}")
        return WorkerTaskResult(result=model_result.content)


class OrchestratorAgent(RoutedAgent):
    def __init__(
        self,
        model_client: ChatCompletionClient,
        worker_agent_types: List[str],
        num_layers: int,
    ) -> None:
        super().__init__(description="Aggregator Agent")
        self._model_client = model_client
        self._worker_agent_types = worker_agent_types
        self._num_layers = num_layers

    @message_handler
    async def handle_task(self, message: UserTask, ctx: MessageContext) -> FinalResult:
        print(f"{'-'*80}\nOrchestrator-{self.id}:\nReceived task: {message.task}")
        # Create task for the first layer.
        worker_task = WorkerTask(task=message.task, previous_results=[])
        # Iterate over layers.
        for i in range(self._num_layers - 1):
            # Assign workers for this layer.
            worker_ids = [
                AgentId(worker_type, f"{self.id.key}/layer_{i}/worker_{j}")
                for j, worker_type in enumerate(self._worker_agent_types)
            ]
            # Dispatch tasks to workers.
            print(
                f"{'-'*80}\nOrchestrator-{self.id}:\nDispatch to workers at layer {i}"
            )
            results = await asyncio.gather(
                *[self.send_message(worker_task, worker_id) for worker_id in worker_ids]
            )
            print(
                f"{'-'*80}\nOrchestrator-{self.id}:\nReceived results from workers at layer {i}"
            )
            # Prepare task for the next layer.
            worker_task = WorkerTask(
                task=message.task, previous_results=[r.result for r in results]
            )
        # Perform final aggregation.
        print(f"{'-'*80}\nOrchestrator-{self.id}:\nPerforming final aggregation")
        system_prompt = "You have been provided with a set of responses from various open-source models to the latest user query. Your task is to synthesize these responses into a single, high-quality response. It is crucial to critically evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect. Your response should not simply replicate the given answers but should offer a refined, accurate, and comprehensive reply to the instruction. Ensure your response is well-structured, coherent, and adheres to the highest standards of accuracy and reliability.\n\nResponses from models:"
        system_prompt += "\n" + "\n\n".join(
            [f"{i+1}. {r}" for i, r in enumerate(worker_task.previous_results)]
        )
        model_result = await self._model_client.create(
            [
                SystemMessage(content=system_prompt),
                UserMessage(content=message.task, source="user"),
            ]
        )
        assert isinstance(model_result.content, str)
        return FinalResult(result=model_result.content)


async def main():

    task = "I have 432 cookies, and divide them 3:4:2 between Alice, Bob, and Charlie. How many cookies does each person get?"

    runtime = SingleThreadedAgentRuntime()
    model_client = get_llm_client()
    await WorkerAgent.register(
        runtime, "worker", lambda: WorkerAgent(model_client=model_client)
    )
    await OrchestratorAgent.register(
        runtime,
        "orchestrator",
        lambda: OrchestratorAgent(
            model_client=model_client, worker_agent_types=["worker"] * 3, num_layers=3
        ),
    )

    runtime.start()
    result = await runtime.send_message(
        UserTask(task=task), AgentId("orchestrator", "default")
    )

    await runtime.stop_when_idle()
    await model_client.close()

    print(f"{'-'*80}\nFinal result:\n{result.result}")
