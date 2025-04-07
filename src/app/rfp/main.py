import asyncio
from pathlib import Path

from autogen_core import (
    AgentId,
    ClosureAgent,
    ClosureContext,
    MessageContext,
    SingleThreadedAgentRuntime,
    TypeSubscription,
)
from openai import BaseModel

from app.rfp.agents.extractor import ExtractorAgent
from app.rfp.agents.manager import ManagerAgent, Results, StartMessage
from app.rfp.agents.section_generator import SectionGeneratorAgent
from app.rfp.utils import Agents, Topics

queue = asyncio.Queue[Results]()


async def main():

    runtime = SingleThreadedAgentRuntime()

    print("Starting")
    manager_agent_type = await ManagerAgent.register(
        runtime,
        Agents.MANAGER.value,
        lambda: ManagerAgent(Agents.MANAGER.value),
    )

    sub = TypeSubscription(Topics.START.value, manager_agent_type)
    await runtime.add_subscription(sub)
    sub = TypeSubscription(Topics.PARSED.value, manager_agent_type)
    await runtime.add_subscription(sub)
    sub = TypeSubscription(Topics.EXTRACTED.value, manager_agent_type)
    await runtime.add_subscription(sub)
    sub = TypeSubscription(Topics.GENERATED.value, manager_agent_type)
    await runtime.add_subscription(sub)

    extractor_agent_type = await ExtractorAgent.register(
        runtime,
        Agents.EXTRACTOR.value,
        lambda: ExtractorAgent(Agents.EXTRACTOR.value),
    )
    sub = TypeSubscription(Topics.EXTRACT.value, extractor_agent_type)
    await runtime.add_subscription(sub)

    section_generator_agent_type = await SectionGeneratorAgent.register(
        runtime,
        Agents.SECTION_GENERATOR.value,
        lambda: SectionGeneratorAgent(Agents.SECTION_GENERATOR.value),
    )
    sub = TypeSubscription(Topics.GENERATE.value, section_generator_agent_type)
    await runtime.add_subscription(sub)

    runtime.start()

    async def collect_result(
        _agent: ClosureContext, message: Results, ctx: MessageContext
    ) -> None:
        await queue.put(message)

    await ClosureAgent.register_closure(
        runtime,
        "closure",
        collect_result,
        subscriptions=lambda: [
            TypeSubscription(topic_type="results", agent_type="closure")
        ],
    )

    # Start the process
    sample_file_path = str(Path.cwd() / "sample_pdf.pdf")
    agent_id = AgentId(Agents.MANAGER.value, "default")
    await runtime.send_message(
        StartMessage(question_file_path=sample_file_path),
        agent_id,
    )
    await runtime.stop_when_idle()

    while not queue.empty():
        print(await queue.get())
