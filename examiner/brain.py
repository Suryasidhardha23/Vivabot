import google.generativeai as genai
import time
import re
import random
import os

# 1. Load keys safely and remove any that are missing (None)
API_KEYS = [
    key for key in [
        os.environ.get("GEMINI_KEY_1"),
        os.environ.get("GEMINI_KEY_2"),
        os.environ.get("GEMINI_KEY_3")
    ]
    if key is not None  # <--- CRITICAL: filters out None values
]

# Optional: Stop app from starting if NO keys are found at all
if not API_KEYS:
    raise RuntimeError("No Gemini API keys found! Set GEMINI_KEY_1, etc. in environment.")

class MockBrain:
    def __init__(self):
        self.keys = API_KEYS
        self.current_key_index = 0
        # Recommended: Use specific model version for stability
        self.model_name = "gemini-1.5-flash" 

    def _rotate_key(self):
        """Switches to the next API Key in the list"""
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        print(f"🔄 Quota hit! Switching to Key #{self.current_key_index + 1}")

    def _generate_content_safe(self, prompt):
        """Wrapper to call Gemini with Key Rotation"""
        # Attempt loop: Try each key once before giving up
        for attempt in range(len(self.keys)):
            try:
                # Configure active key
                active_key = self.keys[self.current_key_index]
                genai.configure(api_key=active_key)
                model = genai.GenerativeModel(self.model_name)
                
                # Call API
                response = model.generate_content(prompt)
                return response.text.strip()

            except Exception as e:
                error_msg = str(e)
                # Check for quota limits (429) or Service Unavailable (503)
                if "429" in error_msg or "ResourceExhausted" in error_msg:
                    self._rotate_key()
                    time.sleep(1) # Brief pause
                else:
                    raise e # Real error (like bad prompt), don't retry
                    
        return "Error: All API keys exhausted quota."

    def generate_question(self, topic, context_text=None):
        try:
            time.sleep(2) # Safety delay
            
            if context_text:
                # --- PDF MODE ---
                safe_text = context_text[:3000] 
                prompt = f"""
                Act as an expert examiner.
                I have uploaded a document. Here is a snippet:
                "{safe_text}..."
                
                Task: Ask ONE specific viva question based on this text.
                Constraint: Keep it under 20 words. Do not give the answer.
                """
            else:
                # --- STANDARD TOPIC MODE ---
                prompt = f"""
                Act as a strict but fair computer science professor.
                Topic: {topic}
                Task: Ask ONE short, conceptual interview question about {topic}.
                Constraint: Keep it under 20 words. Do not give the answer.
                """

            return self._generate_content_safe(prompt)
            
        except Exception as e:
            return f"Error: {str(e)}"

    def evaluate_answer(self, current_question, user_answer, context=None,topic="General Viva"):
        try:
            time.sleep(2) 

            # 1. Context Setup
            if context:
                safe_context = context[:3000]
                context_instruction = f"Context: Student is answering based on this document:\n{safe_context}"
            else:
                context_instruction = f"Context: This is a viva exam specifically on the topic: '{topic}'."

            # 2. Strict Prompt
            prompt = f"""
            Act as a strict Examiner.
            {context_instruction}
            Current Question: "{current_question}"
            Student Answer: "{user_answer}"
            
            Task:
            1. Grade it (0-100).
            2. Give 1 sentence of feedback.
            3. Provide the IDEAL correct answer (max 1 sentence).
            4. Ask a short FOLLOW-UP question.
            
            CRITICAL: Use this format strictly:
            Score: [num] || Feedback: [text] || IdealAnswer: [text] || Followup: [text]
            """

            # 3. Safe Generation
            response_text = self._generate_content_safe(prompt)
            
                        # ... inside evaluate_answer ...
            
            # 4. Robust Regex Parsing
            # SCORE: Look for ANY number after "Score:"
            score_match = re.search(r"Score:\s*(\d+)", response_text, re.IGNORECASE)
            score = int(score_match.group(1)) if score_match else 0

            # FEEDBACK: Take text between "Feedback:" and "IdealAnswer" (or ||)
            feed_match = re.search(r"Feedback:\s*(.*?)(?=\s*(?:\|\||IdealAnswer:|Followup:|$))", response_text, re.IGNORECASE | re.DOTALL)
            feedback = feed_match.group(1).strip() if feed_match else "Feedback unavailable."

            # IDEAL ANSWER: Take text between "IdealAnswer:" and "Followup"
            ideal_match = re.search(r"IdealAnswer:\s*(.*?)(?=\s*(?:\|\||Followup:|$))", response_text, re.IGNORECASE | re.DOTALL)
            ideal = ideal_match.group(1).strip() if ideal_match else "N/A"

            # NEXT QUESTION: Look for "Followup:" OR "Next Question:"
            # This captures everything until the end of the string
            next_match = re.search(r"(?:Followup|Next Question|Next):\s*(.*)", response_text, re.IGNORECASE | re.DOTALL)
            next_q = next_match.group(1).strip() if next_match else "Let's move to the next topic."

            # Safety fallback if Next Question is still empty/undefined
            if not next_q or next_q.lower() == "undefined":
                next_q = "Tell me about a key concept in this topic."

            return {
                "score": score,
                "feedback": feedback,
                "ideal_answer": ideal,
                "next_question": next_q
            }


        except Exception as e:
            print(f"Brain Error: {e}")
            return {"score": 0, "feedback": "System Error", "ideal_answer": "Error", "next_question": "Error"}

    def generate_report(self, history_text):
        try:
            prompt = f"""
            Act as a Senior Professor. 
            Review this viva session history:
            {history_text}
            
            Task: Generate a final performance report.
            Return ONLY JSON:
            {{
                "grade": "A/B/C/F",
                "strengths": ["point1", "point2"],
                "weaknesses": ["point1", "point2"],
                "final_verdict": "One sentence summary."
            }}
            """
            return self._generate_content_safe(prompt)
        except:
            return "{}"
