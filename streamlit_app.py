import asyncio
import os
import sys
import tempfile
from pathlib import Path

import streamlit as st
from autogen_core import (
    AgentId,
    ClosureAgent,
    ClosureContext,
    MessageContext,
    SingleThreadedAgentRuntime,
    TypeSubscription,
)

# Add the src directory to the Python path
src_path = str(Path(__file__).parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from app.core.llm_tracker import (
    get_global_tracker,
    reset_global_tracker,
    setup_tracking,
)
from app.rfp.agents.extractor import ExtractorAgent
from app.rfp.agents.manager import ManagerAgent, Results, StartMessage
from app.rfp.agents.section_generator import SectionGeneratorAgent
from app.rfp.services.file import FileProcessing
from app.rfp.utils import Agents, Topics

queue = asyncio.Queue[Results]()


# Function to initialize the app
def main():
    # Initialize session state variables if they don't exist
    if "runtime" not in st.session_state:
        st.session_state.runtime = None
    if "manager_agent_id" not in st.session_state:
        st.session_state.manager_agent_id = None
    if "results" not in st.session_state:
        st.session_state.results = None
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "kb_files" not in st.session_state:
        st.session_state.kb_files = []
    if "weaviate_service" not in st.session_state:
        st.session_state.weaviate_service = None
    if "token_usage" not in st.session_state:
        st.session_state.token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "model_calls": 0,
        }

    # Initialize services
    file_service = FileProcessing()

    # Set page config
    st.set_page_config(
        page_title="RFP Question Answering", page_icon="📝", layout="centered"
    )

    # Main title
    st.title("📝 RFP Question Answering System")
    st.markdown(
        "Upload a question file, proposal file, and knowledge base files (max 3) to get answers to your questions."
    )

    # Create the app layout and functionality
    create_app_layout(file_service)


async def initialize_runtime():
    """Initialize the agent runtime and register agents."""
    runtime = SingleThreadedAgentRuntime()

    # Register the manager agent
    manager_agent_type = await ManagerAgent.register(
        runtime,
        Agents.MANAGER.value,
        lambda: ManagerAgent(Agents.MANAGER.value),
    )

    # Add subscriptions for the manager agent
    await runtime.add_subscription(
        TypeSubscription(Topics.START.value, manager_agent_type)
    )
    await runtime.add_subscription(
        TypeSubscription(Topics.PARSED.value, manager_agent_type)
    )
    await runtime.add_subscription(
        TypeSubscription(Topics.EXTRACTED.value, manager_agent_type)
    )
    await runtime.add_subscription(
        TypeSubscription(Topics.GENERATED.value, manager_agent_type)
    )

    # Register the extractor agent
    extractor_agent_type = await ExtractorAgent.register(
        runtime,
        Agents.EXTRACTOR.value,
        lambda: ExtractorAgent(Agents.EXTRACTOR.value),
    )
    await runtime.add_subscription(
        TypeSubscription(Topics.EXTRACT.value, extractor_agent_type)
    )

    # Register the section generator agent
    section_generator_agent_type = await SectionGeneratorAgent.register(
        runtime,
        Agents.SECTION_GENERATOR.value,
        lambda: SectionGeneratorAgent(Agents.SECTION_GENERATOR.value),
    )
    await runtime.add_subscription(
        TypeSubscription(Topics.GENERATE.value, section_generator_agent_type)
    )

    return runtime


async def process_question_file(file_bytes, file_name):
    """Process a question file using the agent runtime and track token usage."""
    # Create a temporary file to store the question file
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=f".{file_name.split('.')[-1]}"
    ) as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name

    try:
        # Set up token tracking
        reset_global_tracker()
        setup_tracking()

        # Initialize the runtime if not already initialized
        if st.session_state.runtime is None:
            st.session_state.runtime = await initialize_runtime()
            st.session_state.runtime.start()

            # setup closure
            async def collect_result(
                _agent: ClosureContext, message: Results, ctx: MessageContext
            ) -> None:
                await queue.put(message)

            await ClosureAgent.register_closure(
                st.session_state.runtime,
                "closure",
                collect_result,
                subscriptions=lambda: [
                    TypeSubscription(topic_type="results", agent_type="closure")
                ],
            )

        # Create the manager agent ID
        st.session_state.manager_agent_id = AgentId(Agents.MANAGER.value, "default")

        # Send the start message to the manager agent
        await st.session_state.runtime.send_message(
            StartMessage(question_file_path=tmp_path),
            st.session_state.manager_agent_id,
        )

        # Wait for the runtime to complete
        await st.session_state.runtime.stop_when_idle()

        # Get the results from the manager agent
        results = await queue.get()

        # Get token usage statistics
        token_usage = get_global_tracker().get_usage_stats()

        # Update session state with token usage
        st.session_state.token_usage = token_usage

        return results

    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def create_app_layout(file_service):
    """Create the app layout and functionality."""
    # Create a two-column layout
    # col1, col2 = st.columns([1, 2])

    # Questions File Upload
    st.markdown("### Questions File")
    question_file = st.file_uploader(
        "Upload a file containing questions",
        type=["pdf", "txt", "docx", "xlsx", "csv"],
        key="question-file",
        accept_multiple_files=False,
    )

    # Proposal File Upload
    # st.markdown("### Proposal File")
    # proposal_file = st.file_uploader(
    #     "Upload a proposal file (optional)",
    #     type=["pdf", "txt", "docx", "xlsx", "csv"],
    #     key="proposal-file",
    # )

    # # Knowledge Base Files Upload
    # st.markdown("### Knowledge Base Files (max 3)")
    # kb_files = st.file_uploader(
    #     "Upload knowledge base files (max 3)",
    #     type=["pdf", "txt", "docx", "xlsx", "csv"],
    #     accept_multiple_files=True,
    #     key="kb",
    # )

    # Display warning if more than 3 KB files are uploaded
    # if kb_files and len(kb_files) > 3:
    #     st.warning(
    #         "⚠️ Maximum 3 knowledge base files allowed. Only the first 3 will be processed."
    #     )

    # Process button
    if st.button("Generate"):
        if not question_file:
            st.error("❌ Please upload a question file.")
        else:
            st.session_state.processing = True

            # Store KB files for later use
            # st.session_state.kb_files = kb_files[:3] if kb_files else []

            # Process the question file
            with st.spinner("Processing question file..."):
                try:
                    # Process the question file using the agent runtime
                    st.session_state.results = asyncio.run(
                        process_question_file(question_file.read(), question_file.name)
                    )
                    st.success("✅ Question file processed successfully!")
                except Exception as e:
                    st.error(f"❌ Error processing question file: {str(e)}")
                    st.session_state.results = None

            st.session_state.processing = False

    # Display processing status
    if st.session_state.processing:
        st.info("⏳ Processing question file...")

    # Display token usage statistics if available
    if (
        st.session_state.token_usage
        and st.session_state.token_usage["total_tokens"] > 0
    ):
        st.subheader("Token Usage Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Prompt Tokens", st.session_state.token_usage["prompt_tokens"])
        with col2:
            st.metric(
                "Completion Tokens", st.session_state.token_usage["completion_tokens"]
            )
        with col3:
            st.metric("Total Tokens", st.session_state.token_usage["total_tokens"])

        st.metric("Model API Calls", st.session_state.token_usage["model_calls"])

    # Display results if available
    if st.session_state.results:

        # Display problem statement if available
        if st.session_state.results.problem_statement:
            st.write("## Problem Statement")
            st.markdown(st.session_state.results.problem_statement)

        # Display requirements if available
        if st.session_state.results.requirements:
            st.write("## Requirements")
            st.markdown(st.session_state.results.requirements)

        # Display expectations if available
        if st.session_state.results.expectations:
            st.write("## Expectations")
            st.markdown(st.session_state.results.expectations)

        # Display sections and questions if available
        if st.session_state.results.sections:
            st.markdown("### Sections and Questions")
            for i, section in enumerate(st.session_state.results.sections):
                # Expand the first box
                with st.expander(f"Section {i+1}: {section.title}", expanded=(i == 0)):
                    for j, question in enumerate(section.questions):
                        st.markdown(f"**Q{j+1}:** {question}")

                        # Add a button to answer the question using KB if KB files are available
                        if st.session_state.kb_files and st.button(
                            f"Answer using KB", key=f"answer_btn_{i}_{j}"
                        ):
                            st.info(
                                "This functionality requires the KB integration to be implemented."
                            )
    else:
        st.info("Upload a question file and click 'Generate' to see results.")


# Add this at the end of the file to run the app when executed directly
if __name__ == "__main__":
    main()
