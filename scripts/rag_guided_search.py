#!/usr/bin/env python3
"""
Vesuvius Autoresearch: RAG-Guided Hyperparameter Search
Wraps the villa/discord_chatbot to provide community-driven search guidance.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add villa paths
VILLA_CHATBOT_DIR = os.path.abspath("villa/discord_chatbot")
if VILLA_CHATBOT_DIR not in sys.path:
    sys.path.append(VILLA_CHATBOT_DIR)


def get_rag_guidance(
    query, vector_store="./villa/discord_chatbot/discord_vector_store"
):
    """
    Queries the Discord RAG chatbot for community insights.
    """
    try:
        from rag_chatbot import DiscordRAGChatbot

        if not os.path.exists(vector_store):
            return {
                "error": f"Vector store not found at {vector_store}. Please run 'python villa/discord_chatbot/build_rag.py' first.",
                "recommendation": None,
            }

        chatbot = DiscordRAGChatbot(vector_store_path=vector_store)
        response = chatbot.query(query)

        return {
            "answer": response.get("answer"),
            "sources": response.get("sources", []),
        }
    except ImportError as e:
        return {"error": f"Failed to import RAG chatbot: {e}", "recommendation": None}
    except Exception as e:
        return {"error": str(e), "recommendation": None}


def main():
    parser = argparse.ArgumentParser(
        description="Query Discord RAG for hyperparameter guidance"
    )
    parser.add_argument(
        "--query", required=True, help="Question for the community knowledge base"
    )
    parser.add_argument(
        "--vector-store", default="./villa/discord_chatbot/discord_vector_store"
    )
    args = parser.parse_args()

    print("--- RAG-Guided Search: Querying Community Knowledge ---")
    print(f"Query: {args.query}")

    result = get_rag_guidance(args.query, args.vector_store)

    if "error" in result:
        print(f"\n[ERROR] {result['error']}")
        sys.exit(1)

    print("\n--- Community Insight ---")
    print(result["answer"])

    if result["sources"]:
        print("\n--- Sources ---")
        for i, src in enumerate(result["sources"][:3]):
            print(
                f"[{i + 1}] {src.get('author', 'User')} in #{src.get('channel', 'general')}: {src.get('content')[:100]}..."
            )


if __name__ == "__main__":
    main()
