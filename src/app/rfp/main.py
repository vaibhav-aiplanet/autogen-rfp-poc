from pathlib import Path

from autogen_core import AgentId, SingleThreadedAgentRuntime, TypeSubscription

from app.rfp.agents.extractor import ExtractorAgent
from app.rfp.agents.manager import ManagerAgent, StartMessage
from app.rfp.agents.section_generator import SectionGeneratorAgent
from app.rfp.utils import Agents, Topics


async def main():
    with SingleThreadedAgentRuntime() as runtime:
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

        # Start the process
        sample_file_path = str(Path.cwd() / "sample_pdf.pdf")
        agent_id = AgentId(Agents.MANAGER.value, "default")
        await runtime.send_message(
            StartMessage(question_file_path=sample_file_path),
            agent_id,
        )
        await runtime.stop_when_idle()
