import json
import re
import time
import google.generativeai as genai
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from PyPDF2 import PdfReader

# Import your Brain (Assuming it's in brain.py)
from .brain import MockBrain

# Initialize the AI Brain
brain = MockBrain()

def landing(request):
    """Renders the animated landing page"""
    return render(request, 'landing.html')

def chat(request):
    """Renders the main chat interface"""
    return render(request, 'index.html')

@csrf_exempt
def start_interview(request):
    """API: Starts the interview and resets the counter"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            topic = data.get("topic", "General CS")
            
            # --- RESET SESSION (Correct Way) ---
            request.session["question_count"] = 0
            request.session["topic"] = topic
            request.session["history"] = []
            request.session["scores"] = []
            request.session["pdf_text"] = None # Reset PDF too
            request.session.modified = True
            
            # Generate First Question
            question = brain.generate_question(topic)
            
            return JsonResponse({"message": question}) # Frontend expects "message" (or "question")
        except Exception as e:
            return JsonResponse({"message": f"Error: {str(e)}"}, status=500)
    return JsonResponse({}, status=400)

@csrf_exempt
def submit_answer(request):
    """Evaluates answer, tracks count, and decides next step"""
    if request.method == "POST":
        try:
            # 1. Parse User Input
            data = json.loads(request.body)
            user_answer = data.get("answer", "")
            current_question = data.get("question", "")
            
            # 2. Get Context from Session
            pdf_context = request.session.get('pdf_text', None)
            topic = request.session.get("topic", "General Computer Science")
            count = request.session.get("question_count", 0)
            history = request.session.get("history", [])

            # 3. Use Brain to Evaluate (This handles the Prompting internally now)
            # We use brain.evaluate_answer because it has the Retry/Rotate logic built-in!
            feedback_data = brain.evaluate_answer(current_question, user_answer, context=pdf_context,topic=topic)

            # 4. Update Counters
            count += 1
            request.session['question_count'] = count
            
            # Add to history for Report Card
            history.append(f"Q: {current_question}\nA: {user_answer}\nGrade: {feedback_data['score']}")
            request.session['history'] = history
            request.session.modified = True

           # 5. CHECK FOR REPORT CARD (The "Game Over" Condition)
            if count >= 5:
                # Generate Report
                full_history = "\n".join(history)
                report_json = brain.generate_report(full_history)
                
                # --- FIX: Clean Markdown before parsing ---
                cleaned_json = report_json.strip()
                if cleaned_json.startswith("```"):
                    cleaned_json = re.sub(r"^``````", "", report_json)
                if cleaned_json.endswith("```"):
                    cleaned_json = cleaned_json[:-3].strip()
                # ------------------------------------------

                try:
                    report_data = json.loads(cleaned_json)
                except json.JSONDecodeError:
                    print(f"Report JSON Error: {report_json}") # Debug print
                    report_data = {
                        "grade": "Completed", 
                        "strengths": ["Completed 5 questions"], 
                        "weaknesses": ["Review needed"], 
                        "final_verdict": "Good effort! Check the console for details."
                    }

                return JsonResponse({
                    "status": "completed",
                    "score": feedback_data['score'],
                    "feedback": feedback_data['feedback'],
                    "report": report_data
                })

            # 6. Return Normal Feedback (Next Question)
            return JsonResponse({
                "status": "next",
                "score": feedback_data['score'],
                "feedback": feedback_data['feedback'],
                "ideal_answer": feedback_data['ideal_answer'],
                "next_question": feedback_data['next_question']
            })

        except Exception as e:
            print(f"Server Error: {e}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "POST request required"}, status=400)

@csrf_exempt
def upload_pdf(request):
    """API: Handles PDF upload and extracts text"""
    if request.method == "POST" and request.FILES.get('pdf_file'):
        try:
            pdf_file = request.FILES['pdf_file']
            reader = PdfReader(pdf_file)
            text = ""
            for page in reader.pages[:5]: # Limit to first 5 pages for speed
                text += page.extract_text()
            
            # Save to Session
            request.session["pdf_text"] = text
            request.session["topic"] = "Uploaded Document"
            request.session["question_count"] = 0
            request.session["history"] = []
            request.session.modified = True
            
            # Generate First Question from PDF
            question = brain.generate_question("Document", context_text=text)
            
            return JsonResponse({"message": question, "status": "success"})
            
        except Exception as e:
            return JsonResponse({"message": f"Error reading PDF: {str(e)}"}, status=500)
            
    return JsonResponse({"message": "No file found"}, status=400)
