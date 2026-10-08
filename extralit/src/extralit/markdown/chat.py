import markdown

CHAT_CSS_STYLE = """
    <style>
        .user-message, .system-message {
            display: flex;
            margin: 10px;
        }
        .user-message {
            justify-content: flex-end;
        }
        .system-message {
            justify-content: flex-start;
        }
        .user-message .message-content {
            background-color: #c2e3f7;
            color: #000000;
        }
        .system-message .message-content {
            background-color: #f5f5f5;
            color: #000000;
        }
        .message-content {
            padding: 10px;
            border-radius: 10px;
            max-width: 80%;
        }
    </style>
    """


def chat_to_html(messages: list[dict[str, str]]) -> str:
    """
    Converts a list of chat messages in the OpenAI format to HTML.

    Args:
        messages (List[Dict[str, str]]): A list of dictionaries where each dictionary represents a chat message.
            Each dictionary should have the keys:
                - "role": A string indicating the role of the sender (e.g., "user", "model", "assistant", "system").
                - "content": The content of the message.

    Returns:
        str: An HTML string that represents the chat conversation.

    Raises:
        ValueError: If the an invalid role is passed.

    Examples:
        ```python
        from extralit.markdown import chat_to_html
        html = chat_to_html([
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "goodbye"}
        ])
        ```
    """
    chat_html = ""
    for message in messages:
        role = message["role"]
        content = message["content"]
        content_html = markdown.markdown(content)

        if role == "user":
            html = '<div class="user-message">' + '<div class="message-content">'
        elif role in ["model", "assistant", "system"]:
            html = '<div class="system-message">' + '<div class="message-content">'
        else:
            raise ValueError(f"Invalid role: {role}")

        html += f"{content_html}"
        html += "</div></div>"
        chat_html += html

    return f"<body>{CHAT_CSS_STYLE}{chat_html}</body>"
