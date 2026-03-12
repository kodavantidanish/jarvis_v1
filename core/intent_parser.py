from groq import Groq
import json
import config

class IntentParser:
    def __init__(self):
        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.model = config.GROQ_MODEL

    def parse(self, user_input):
        """Parse intent from user input — used for action detection only."""
        prompt = f"""You are JARVIS, a desktop assistant for Windows.
Analyze this command: "{user_input}"

Respond with ONLY a JSON object (no markdown, no explanation):
{{
    "action": "open_folder" or "open_file" or "open_app" or "chat",
    "target": "what to open (if applicable, else null)",
    "path": "full path if known, else file type hint (word/pdf/ppt/excel/image) for files, else null",
    "response": "friendly reply to user"
}}

IMPORTANT RULES:
1. If user says "open [something]", it's ALWAYS open_folder, open_file, or open_app — NEVER chat
2. For "target" field, use SHORT names (e.g., "Word" not "Microsoft Word")
3. Single words after "open" are usually folder/app names, not chat topics
4. If user says "open [letter] drive" or "open [letter]:" set path to "[LETTER]:\\" directly
5. Drive letters are ALWAYS open_folder, never open_app or chat
6. Greetings, questions, or anything NOT about opening files/apps is ALWAYS "chat"
7. If unsure between chat and open, only use open if the word "open", "launch", or "start" is present
8. If user says "open [filename]" and it sounds like a document (has extension or words like report, resume, invoice, notes, budget), use "open_file"
9. For open_file, put file type hint in "path" field (word/pdf/ppt/excel/image) if known, else null
10. For "target", ALWAYS keep the FULL name exactly as the user typed it — including dates, numbers, brackets, dashes. NEVER shorten or trim it.
11. For folder names, keep the FULL name including everything after dashes. e.g. "UD - Unit 3" stays as "UD - Unit 3"
12. If the user includes a file extension (.pdf, .docx, .pptx etc.), strip ONLY the extension for "target" but use it to set the correct "path" type hint

Examples:

User: "hi"
{{"action": "chat", "target": null, "path": null, "response": "Hey! How can I help you?"}}

User: "open downloads"
{{"action": "open_folder", "target": "downloads", "path": null, "response": "Opening downloads folder."}}

User: "open d drive"
{{"action": "open_folder", "target": "d_drive", "path": "D:\\\\", "response": "Opening D drive."}}

User: "open chrome"
{{"action": "open_app", "target": "chrome", "path": null, "response": "Launching Chrome."}}

User: "open Danish_resume(01-2026).pdf"
{{"action": "open_file", "target": "Danish_resume(01-2026)", "path": "pdf", "response": "Opening your resume."}}

JSON:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200
            )

            result = response.choices[0].message.content.strip()

            if "```json" in result:
                result = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                result = result.split("```")[1].split("```")[0].strip()

            return json.loads(result)

        except Exception as e:
            if config.DEBUG_MODE:
                print(f"Parser error: {e}")
            return {
                "action": "chat",
                "target": None,
                "path": None,
                "response": "I didn't quite understand that."
            }

    def chat(self, user_input, conversation_history):
        """
        Handle conversational replies using full conversation history.
        conversation_history: list of {"role": "user"/"assistant", "content": "..."}
        """
        system_prompt = """You are JARVIS, an intelligent Windows desktop assistant inspired by Iron Man's JARVIS.
You have a sharp, witty, and helpful personality — like a knowledgeable friend who also manages your computer.

You can:
- Open folders, files, and applications
- Search the file system
- Remember everything done in this session

When the user asks what you've done or for a summary, refer back to the conversation history.
Keep responses concise but warm. Never say "as an AI" — you are JARVIS."""

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_input})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=300
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            if config.DEBUG_MODE:
                print(f"Chat error: {e}")
            return "Sorry, I ran into an issue responding to that."