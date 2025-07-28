from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
import json
import os
from rapidfuzz import fuzz, process

app = FastAPI()

# تثبيت مجلد static
app.mount("/static", StaticFiles(directory="static"), name="static")

# مجلدات الجلسات والتقييمات
SESSIONS_DIR = "sessions"
FEEDBACK_DIR = "feedback"
UNANSWERED_FILE = "unanswered_questions.json"
os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(FEEDBACK_DIR, exist_ok=True)

# نماذج البيانات
class ChatMessage(BaseModel):
    session_id: str
    message: str

class Feedback(BaseModel):
    session_id: str
    rating: int
    comment: str = ""

# حفظ الأسئلة غير المفهومة
def save_unanswered_question(question: str):
    data = []
    if os.path.exists(UNANSWERED_FILE):
        try:
            with open(UNANSWERED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []
    data.append({"question": question})
    with open(UNANSWERED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# تحميل قاعدة المعرفة
def load_knowledge_base():
    with open("knowledge_base.json", encoding="utf-8") as f:
        return json.load(f)

# الرد الافتراضي
DEFAULT_RESPONSE = (
    "عذرًا، لم أتمكن من تحديد استفسارك بدقة. "
    "للتواصل مع الفريق المختص، يُرجى مراسلتنا عبر البريد: info@jec.sa.com "
    "أو من خلال نموذج التواصل على موقعنا."
)

# إيجاد أفضل إجابة
# دالة إيجاد أفضل إجابة
def find_best_answer(user_question: str):
    kb = load_knowledge_base()
    best_match = None
    best_score = 0

    # المحاولة الأولى: تطابق دقيق باستخدام rapidfuzz
    for item in kb:
        if not item["questions"]:  # تجاهل العناصر الفارغة
            continue

        result = process.extractOne(user_question, item["questions"], score_cutoff=90)
        if result:
            match, score, _ = result
            if score > best_score:
                best_score = score
                best_match = item["answer"]

    if best_match:
        return best_match

    # المحاولة الثانية: تطابق جزئي لكن بدقة عالية
    for item in kb:
        if not item["questions"]:
            continue

        for q in item["questions"]:
            partial_score = fuzz.partial_ratio(user_question, q)
            if partial_score >= 90:
                return item["answer"]

    # الرد الافتراضي إذا لم يتم العثور على تطابق
    print(f"[DEBUG] لم يتم التعرف على السؤال: {user_question}")
    return DEFAULT_RESPONSE

# API: المحادثة
@app.post("/chat")
async def chat(message: ChatMessage):
    try:
        session_path = os.path.join(SESSIONS_DIR, f"{message.session_id}.json")
        session_data = []

        if os.path.exists(session_path):
            with open(session_path, "r", encoding="utf-8") as f:
                session_data = json.load(f)

        bot_response = find_best_answer(message.message)

        print("[DEBUG] user_message:", message.message)
        print("[DEBUG] bot_response:", bot_response)

        session_data.append({"role": "user", "content": message.message})
        session_data.append({"role": "assistant", "content": bot_response})

        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

        return {"response": bot_response}

    except Exception as e:
        print("[ERROR] Exception in /chat:", e)
        return JSONResponse(
            content={"response": "حدث خطأ داخلي أثناء المعالجة. سيتم تحويل سؤالك إلى الفريق المختص."},
            status_code=500
        )

# API: استرجاع الجلسة
@app.get("/get-session/{session_id}")
async def get_session(session_id: str):
    session_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if not os.path.exists(session_path):
        return []
    with open(session_path, "r", encoding="utf-8") as f:
        return json.load(f)

# API: حذف الجلسة
@app.delete("/reset-session/{session_id}")
async def delete_session(session_id: str):
    session_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if os.path.exists(session_path):
        os.remove(session_path)
    return {"status": "deleted"}

# API: استقبال التقييم
@app.post("/feedback")
async def submit_feedback(feedback: Feedback):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    feedback_path = os.path.join(FEEDBACK_DIR, f"{feedback.session_id}_{timestamp}.json")

    entry = {
        "timestamp": datetime.now().isoformat(),
        "rating": feedback.rating,
        "comment": feedback.comment
    }
    with open(feedback_path, "w", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False, indent=2)
    return {"status": "feedback saved"}

# API: جميع التقييمات
@app.get("/all-feedbacks")
async def get_all_feedbacks():
    all_data = []
    for filename in os.listdir(FEEDBACK_DIR):
        path = os.path.join(FEEDBACK_DIR, filename)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                content = json.load(f)
                session_id = filename.replace(".json", "")
                content["session_id"] = session_id
                all_data.append(content)
    return all_data

# واجهة لوحة التقييمات
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    with open("static/dashboard.html", encoding="utf-8") as f:
        return f.read()

# الواجهة الرئيسية
@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()
    
# API: عرض الأسئلة غير المفهومة كـ JSON
@app.get("/get-unanswered")
async def get_unanswered_questions():
    if not os.path.exists(UNANSWERED_FILE):
        return []
    with open(UNANSWERED_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# واجهة عرض الأسئلة غير المفهومة
@app.get("/unanswered", response_class=HTMLResponse)
async def unanswered_page():
    with open("static/unanswered.html", encoding="utf-8") as f:
        return f.read()
