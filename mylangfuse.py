import os
from langfuse.decorators import observe
from langfuse.openai import openai  # OpenAI integration
from openai import OpenAI
from arklex.utils.model_config import MODEL
from dotenv import load_dotenv

load_dotenv()

@observe
def chatgpt_chatbot(messages, model=MODEL["model_type_or_path"]):
    if MODEL["llm_provider"] == "deepseek":
        client = OpenAI(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url=os.environ["DEEPSEEK_API_URL"],
        )
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,
    )
    answer = completion.choices[0].message.content.strip()
    return answer

@observe()
def story():
    return openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a great storyteller."},
            {"role": "user", "content": "Once upon a time in a galaxy far, far away..."}
        ],
    ).choices[0].message.content



if __name__ == "__main__":
    messages = [
        {"role": "system", "content": "You are a great storyteller."},
        {"role": "user", "content": "Once upon a time in a galaxy far, far away..."}
    ]
    chatgpt_chatbot(messages)