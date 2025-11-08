import json, re, textwrap, os
import streamlit as st

# ============ Рубрика ============
def _tok(text:str):
    return re.findall(r"[A-Za-zӘәҒғҚқҢңӨөҰұҮүҺһІіЁёА-Яа-я]+", text.lower())

def _bounded(x, lo=0, hi=9):
    try: return float(min(max(float(x), lo), hi))
    except: return 0.0

def _overall(scores:dict):
    w = {"content":0.30,"coherence":0.20,"lexis":0.20,"grammar":0.20,"style":0.10}
    s = sum(_bounded(scores.get(k,0))*w[k] for k in w)
    return round(s*2)/2

def grade_heuristic(essay:str):
    words = _tok(essay); n = len(words)
    sents = [s for s in re.split(r"[.!?…]+", essay) if s.strip()]
    avg_sent = n/len(sents) if sents else 0
    ttr = len(set(words))/n if n else 0
    connectors = {"біріншіден","екіншіден","сондықтан","демек","алайда","сонымен","яғни","соңында","қорытындылай"}
    conn_hits = sum(w in connectors for w in words)

    scores = {
        "content": float(min(9, 3 + n//120)),
        "coherence": float(min(9, 3 + conn_hits//1)),
        "lexis": float(min(9, 3 + int(ttr*10))),
        "grammar": float(min(9, 4 + int(max(0, 1 - abs(avg_sent-18)/18)*5))),
        "style": float(min(9, 4 + int(min(0.2, sum(len(w)>=8 for w in words)/max(1,n))*25))),
    }
    overall = _overall(scores)

    strengths, issues = [], []
    if conn_hits >= 2: strengths.append("Логикалық дәнекер сөздер қолданылған.")
    if ttr > 0.45: strengths.append("Лексикалық әртүрлілік жақсы деңгейде.")
    if 14 <= avg_sent <= 24: strengths.append("Сөйлем ұзындықтары оқылымды.")
    if not strengths: strengths.append("Негізгі ой айқын.")

    if n < 180: issues.append("Эссе көлемі шағын; аргументтерді мысалмен толықтыр.")
    if conn_hits < 2: issues.append("Абзацаралық байланыстар әлсіз.")
    if ttr < 0.35: issues.append("Сөздердің қайталануы байқалады; синоним қолдан.")

    suggestions = [
        {"title":"Дәлелді тереңдету","how_to_fix":"Әр тезиске нақты дерек/сілтеме/мысал қос.","example_before":"«Жастар оқымайды.»","example_after":"«PISA 2022 дерегі бойынша ... Сонымен қатар, мектеп кітапханасында ...»"},
        {"title":"Құрылымды нығайту","how_to_fix":"Абзац бастарын сигнал сөздермен белгіле («Біріншіден/Екіншіден/Сондықтан»).","example_before":"«Бағдарлама жаңару керек. Кітапханалардың рөлі бар.»","example_after":"«Біріншіден, бағдарламаны жаңарту қажет. Екіншіден, кітапханалардың рөлі ...»"},
    ]
    summary = (
        "Эссе идеясы түсінікті. Құрылымды бекіту үшін сигнал сөздерді жиірек пайдалан, "
        "дәлелдерді нақты дерек пен қысқа дәйексөздермен нығайт. Лексикалық әртүрлілікті арттырып, "
        "сөйлем ұзындықтарының балансын сақта."
    )

    return {
        "scores": scores,
        "overall": overall,
        "strengths": strengths,
        "issues": issues,
        "suggestions": suggestions,
        "summary": summary
    }

def md_report(result:dict) -> str:
    s = result["scores"]
    lines = []
    lines.append(f"### 🧾 Жалпы балл: **{result['overall']}/9**")
    lines.append("")
    lines.append("| Критерий | Балл |")
    lines.append("|---|---:|")
    lines.append(f"| Мазмұн (content) | {s.get('content','-')}/9 |")
    lines.append(f"| Құрылым (coherence) | {s.get('coherence','-')}/9 |")
    lines.append(f"| Лексика (lexis) | {s.get('lexis','-')}/9 |")
    lines.append(f"| Грамматика (grammar) | {s.get('grammar','-')}/9 |")
    lines.append(f"| Стиль (style) | {s.get('style','-')}/9 |")
    if result.get("strengths"):
        lines.append("\n**Күшті жақтар:**")
        for t in result["strengths"]: lines.append(f"- {t}")
    if result.get("issues"):
        lines.append("\n**Мәселелер:**")
        for t in result["issues"]: lines.append(f"- {t}")
    if result.get("suggestions"):
        lines.append("\n**Ұсыныстар (нақты әрекетпен):**")
        for sgg in result["suggestions"]:
            lines.append(f"- **{sgg.get('title','Ұсыныс')}** — {sgg.get('how_to_fix','')}")
            if sgg.get("example_before") or sgg.get("example_after"):
                lines.append(f"  - Мысал (бұрын): {sgg.get('example_before','')}")
                lines.append(f"  - Мысал (кейін): {sgg.get('example_after','')}")
    if result.get("summary"):
        lines.append("\n**Кеңейтілген қорытынды:**")
        lines.append(result["summary"])
    return "\n".join(lines)

# ============ UI ============
st.set_page_config(page_title="Kazakh Essay Grader", page_icon="🇰🇿", layout="centered")
st.title("🇰🇿 Kazakh Essay Grader")

st.write("Эссеңді енгіз де, **Бағалау** батырмасын бас.")
essay = st.text_area("Эссе (қазақша)", height=300, placeholder="Мұнда эссе мәтінін қой...")

if st.button("Бағалау"):
    if not essay or len(essay.strip()) < 20:
        st.warning("Эссе тым қысқа. Кемінде 20 таңба енгіз.")
    else:
        result = grade_heuristic(essay)
        st.markdown(md_report(result))
        st.download_button("⬇️ Жүктеу (JSON)", json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"), "essay_report.json", "application/json")
        md = md_report(result) + "\n\n---\n**Эссе:**\n" + textwrap.fill(essay, width=100)
        st.download_button("⬇️ Жүктеу (Markdown)", md.encode("utf-8"), "essay_report.md", "text/markdown")
