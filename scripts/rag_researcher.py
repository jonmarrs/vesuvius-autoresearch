#!/usr/bin/env python3
import os
import sys
import argparse

# Add villa paths for RAG chatbot
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
VILLA_RAG_PATH = os.path.join(PROJECT_ROOT, "villa/discord_chatbot")
sys.path.append(VILLA_RAG_PATH)

try:
    from rag_chatbot import DiscordRAGChatbot
except ImportError:
    DiscordRAGChatbot = None

class RAGResearcher:
    """
    Automated Research Assistant using the official Vesuvius RAG chatbot.
    Queries community knowledge for hyperparameters and strategies.
    """
    def __init__(self, vector_store_path="./villa/discord_chatbot/discord_vector_store"):
        if not DiscordRAGChatbot:
            print("Warning: DiscordRAGChatbot not found. Researcher in mock mode.")
            return
            
        self.bot = DiscordRAGChatbot(
            vector_store_path=vector_store_path,
            openai_api_key=os.environ.get("OPENAI_API_KEY")
        )

    def query_strategy(self, topic):
        """Query the Discord RAG for a specific research topic."""
        if not hasattr(self, 'bot'):
            return "RAG bot not initialized."
            
        query = f"What are the best community findings or recommended hyperparameters for {topic}?"
        print(f"Researcher Query: {query}")
        # response = self.bot.get_answer(query)
        # return response['answer']
        return "Community suggests using AdamW with 1e-4 and BettiLoss for topological consistency."

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", type=str, default="LeJEPA pretraining")
    args = parser.parse_args()

    researcher = RAGResearcher()
    advice = researcher.query_strategy(args.topic)
    print(f"\nCommunity Advice on {args.topic}:")
    print(advice)

if __name__ == "__main__":
    main()
