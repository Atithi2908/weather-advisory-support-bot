"""Entry point CLI for Weather Advisory Support Bot (Phase 1).

Run interactively:
    python -m backend.app.main
or from within backend/ directory:
    python -m app.main

Pass a one-off query:
    python -m backend.app.main "Can I cycle in Bangalore today?"
"""

import sys
import uuid
from typing import Optional

# Ensure standard output can print Unicode characters on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is in sys.path
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from backend.app.config import LLM_MODEL
from backend.app.graph.workflow import create_weather_graph
from backend.app.services.llm_service import is_llm_configured
from backend.app.api import app


def run_query(
    graph,
    user_query: str,
    session_id: str,
    verbose: bool = False,
) -> str:
    """Execute a single query through the LangGraph pipeline with session context."""
    config = {"configurable": {"thread_id": session_id}}
    result = graph.invoke({"user_query": user_query}, config=config)

    if verbose:
        print("\n--- Pipeline State ---")
        print(f"Activity:       {result.get('activity')}")
        print(f"Location:       {result.get('location')}")
        print(f"Resolved Name:  {result.get('resolved_location_name')}")
        print(f"Coordinates:    {result.get('latitude')}, {result.get('longitude')}")
        print(f"Weather data:   {result.get('weather')}")
        sop = result.get('selected_sop')
        if sop:
            print(f"Selected SOP:   {sop.get('id')} ({sop.get('name')}) [{sop.get('severity')}]")
        else:
            print("Selected SOP:   None (No matching guidance)")
        matched = result.get('matched_sops') or []
        print(f"Matched SOPs:   {[s.get('id') for s in matched]}")
        print(f"Error:          {result.get('error')}")
        print("-----------------------\n")

    return result.get("response", "No response generated.")


def main():
    """Main CLI interaction loop."""
    print("=" * 60)
    print("   Weather-Advisory Support Bot - Backend CLI")
    print("=" * 60)

    if is_llm_configured():
        print(f"[Status] OpenRouter LLM integration active (model: {LLM_MODEL}).")
    else:
        print("[Status] LLM_API_KEY is not configured in .env.")
        print("         Running in deterministic factual fallback mode.")
        print("         (To use real OpenRouter LLM, set LLM_API_KEY in .env)")

    print("\nInitialising LangGraph pipeline...")
    graph = create_weather_graph()
    print("Ready!\n")

    # If query was passed via command line arguments, execute once and exit
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        cli_query = " ".join(sys.argv[1:])
        print(f"Query: {cli_query}\n")
        response = run_query(graph, cli_query, session_id="cli-single-shot", verbose=True)
        print("Bot Response:")
        print(response)
        return

    session_id = f"session-{uuid.uuid4().hex[:8]}"
    print("Session started. Type your questions below.")
    print("Commands: 'exit' / 'quit' to quit, 'debug' to toggle state inspection.\n")

    verbose = False
    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting session. Goodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "q"):
            print("Goodbye!")
            break

        if user_input.lower() == "debug":
            verbose = not verbose
            print(f"[Debug state inspection: {'ON' if verbose else 'OFF'}]")
            continue

        response = run_query(graph, user_input, session_id=session_id, verbose=verbose)
        print(f"\nBot:\n{response}\n")


if __name__ == "__main__":
    main()
