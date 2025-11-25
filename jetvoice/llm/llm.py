import openai
from dotenv import load_dotenv
import os
import sys

class JetVoiceLLM:
    def __init__(self, system_prompt: str = None, model: str = "gpt-5.1"):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = model
        
        # Default system prompt if none provided
        self.system_prompt = system_prompt or (
            "You are a helpful voice assistant running on Jetson Nano. "
            "Keep responses brief, conversational, and natural."
        )

        # Configure OpenAI
        if self.api_key:
            openai.api_key = self.api_key

    def ask(self, user_prompt: str) -> str | None:
        """
        Sends a prompt to the LLM and returns the response string.
        """
        if not self.api_key or self.api_key == "your_api_key_here":
            print("[LLM Warning] Invalid or missing OPENAI_API_KEY")
            return None

        try:
            # Using getattr to support openai==0.28.1 structure safely
            chat_completion = getattr(openai, "ChatCompletion")
            
            response = chat_completion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            content = response.choices[0].message["content"].strip()
            return content

        except Exception as e:
            print(f"[OpenAI Error]: {str(e)}")
            return None

if __name__ == "__main__":
    # This block runs when you execute: python -m jetvoice.llm.llm "Your prompt"
    
    # 1. Get prompt from CLI args or default
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = "Hello, introduce yourself briefly."

    print(f"--- Testing JetVoiceLLM ---")
    print(f"Input Prompt: '{prompt}'")

    # 2. Instantiate
    llm = JetVoiceLLM()

    # 3. Check Key (Masked for security)
    if llm.api_key and len(llm.api_key) > 10:
        masked_key = llm.api_key[:6] + "..." + llm.api_key[-4:]
        print(f"API Key found: {masked_key}")
    else:
        print("!! WARNING: API Key appears missing or default !!")

    # 4. Run
    print("Sending request to OpenAI...")
    response = llm.ask(prompt)
    
    print("-" * 30)
    print(f"Response:\n{response}")
    print("-" * 30)