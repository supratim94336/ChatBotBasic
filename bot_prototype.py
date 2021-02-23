from abc import ABCMeta, abstractstaticmethod
from collections import defaultdict
from contextlib import contextmanager
from flask import Flask, request, jsonify
import math
import requests
from typing import Text, Dict, List, Generator

app = Flask(__name__)

inmemory_storage = defaultdict(list)


class Conversation(object):
    def __init__(
        self, conversation_id: Text, old_conversation_events: List[Dict]
    ) -> None:
        """Creates a conversation.
        Args:
            old_conversation_events: Events which happened earlier in this conversation.
        """
        self.conversation_id = conversation_id
        self.conversation_events = old_conversation_events
        self.number_old_events = len(old_conversation_events)

    def add_user_message(self, message: Text) -> None:
        """Adds user's message to the conversation history."""
        self.conversation_events.append({"type": "user", "message": message})

    def add_bot_message(self, bot_messages: Text) -> None:
        """Adds bot's message to the conversation history."""
        self.conversation_events.append({"type": "bot", "message": bot_messages})

    def new_events_dict(self) -> List[Dict]:
        """Returns the conversation history of the new events."""
        return self.conversation_events[self.number_old_events :]


class JokeBot(metaclass=ABCMeta):
    """The bot interface.
    Args: 
        metaclass: To define abstract class.
    """
    @abstractstaticmethod
    def handle_message() -> None:
        """The static interface method"""
        raise NotImplementedError("You need to handle the message!")
    
    @abstractstaticmethod
    def retrieve_joke() -> None:
        """The static interface method"""
        raise NotImplementedError("You need to retrieve the joke!")
    

class ChuckNorrisBot(JokeBot):
    """Creates a bot which returns a random Chuck Norris joke.
    Args:
        JokeBot: Passing the abstract base class.
    """
    def retrieve_joke(self) -> Text:
        """Calls the api to retrieve the random joke.
        Returns:
            The joke in the text format.
        """
        response = requests.get("https://api.chucknorris.io/jokes/random")

        return response.json()["value"]
    
    
    def handle_message(self, message_text: Text, conversation: Conversation) -> None:
        """Adds user's and bot's message to the conversation events.
        Args:
            message_text: The user's message.
            conversation: The Conversation class.
        """
        conversation.add_user_message(message_text)

        if len(conversation.conversation_events) <= 1:
            conversation.add_bot_message(f"Welcome! Let me tell you a joke.")

        joke = self.retrieve_joke()

        conversation.add_bot_message(joke)

    
class ChuckNorrisJokeFinderBot(JokeBot):  
    """Creates a bot which returns a Chuck Norris joke containing 
    the user's message in it.
    Args:
        JokeBot: Passing the abstract base class.
    """
    def retrieve_joke(self, message_text: Text) -> Text:
        """Calls the api to retrieve the joke containing the user's message.
        
        Args:
            message_text: User's message which is the search term in the joke.
        Returns:
            The joke in the text format or the sorry message if no joke is found.
        """
        response = requests.get("https://api.chucknorris.io/jokes/search?query="+message_text)
        
        results = response.json
        
        if results()['result']:
            return results()['result'][0]["value"]
        else:
            return "Phew!! The joke with the text '{}' was hard to find.".format(message_text)
        
        
    def handle_message(self, message_text: Text, conversation: Conversation) -> None:
        """Adds user's and bot's message to the conversation events.
        Args:
            message_text: The user's message.
            conversation: The Conversation class.
        """
        conversation.add_user_message(message_text)

        if len(conversation.conversation_events) <= 1:
            conversation.add_bot_message(f"Welcome! Let me tell you a joke.")

        # retrieve the joke by passing the search text as an argument
        joke = self.retrieve_joke(message_text)
        
        conversation.add_bot_message(joke)


class JokeFactory:
    """Class to declare the factory method."""
    @staticmethod
    def get_relevant_bot(query: Text):
        """Check the query to call the relevant bot.
        
        Args:
            query: Text which decides the relevant bot.
        Returns:
            Object instance of the bot class.
        """
        try:
            if query == "jokeFinder":
                # joke with query term
                return ChuckNorrisJokeFinderBot()
            else:
                # random joke
                return ChuckNorrisBot()
        except AssertionError as _e:
            print("The error is " + _e)
            
        return None
    
    
@contextmanager
def conversationPersistence(
    conversation_id: Text,
) -> Generator[Conversation, None, None]:
    """Provides conversation history for a certain conversation.
    Saves any new events to the conversation storage when the context manager is exited.
    Args:
        conversation_id: The ID of the conversation. This is usually the same as the
            username.
    Returns:
        Conversation from the conversation storage.
    """
    old_conversation_events = inmemory_storage[conversation_id]

    conversation = Conversation(conversation_id, old_conversation_events)

    yield conversation

        
@app.route("/user/<username>/message", methods=["POST"])
def handle_user_message(username: Text) -> Text:
    """Returns a bot response for an incoming user message.
    Args:
        username: The username which serves as unique conversation ID.
    Returns:
        The bot's responses.
    """
    message_text = request.json["text"]
    
    # the query search term
    query_name = request.json['bot_type'] if 'bot_type' in request.json else None
    
    with conversationPersistence(username) as conversation:
        
        f = JokeFactory().get_relevant_bot(query_name)
        
        f.handle_message(message_text, conversation)

        bot_responses = [
            x["message"] for x in conversation.new_events_dict() if x["type"] == "bot"
        ]

        return jsonify(bot_responses)
    

@app.route("/user/<username>/message", methods=["GET"])
def retrieve_conversation_history(username: Text) -> Text:
    """Returns all conversation events for a user's conversation.
    Args:
        username: The username which serves as unique conversation ID.
    Returns:
        All events in this conversation, which includes user and bot messages.
    """
    history = inmemory_storage[username]
    
    if history:
        return jsonify(history), 200
    else:
        return jsonify(history), 404


if __name__ == "__main__":
    print("Server is running")
    app.run(debug=True)
