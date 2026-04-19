import streamlit as st
import pdfplumber
import re
import json
import pandas as pd
import plotly.express as px
from datetime import datetime

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

# -----------------------------------
# 페이지 설정
# -----------------------------------
st.set_page_config(
    page_title="초6 학습자 유형 분석",
    page_icon="📘",
    layout="wide"
)

# -----------------------------------
# 스타일
# -----------------------------------
st.markdown("""
<style>
.block-container {
    padding-top: 1.6rem;
    padding-bottom: 2rem;
}
.main-title {
    font-size: 2rem;
    font-weight: 800;
    color: #1f3c88;
    margin-bottom: 0.2rem;
}
.sub-title {
    color: #555;
    margin-bottom: 1rem;
}
.card {
    background: #f8f9fc;
    border-radius: 16px;
    padding: 20px;
    border: 1px solid #e6e9f2;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    margin-bottom: 16px;
}
.card-title {
    font-size: 1.05rem;
    font-weight: 700;
    margin-bottom: 10px;
    color: #243b6b;
}
.section-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #243b6b;
    margin-top: 1.2rem;
    margin-bottom: 0.8rem;
}
.badge {
    display: inline-block;
    padding: 0.35rem 0.7rem;
    border-radius: 999px;
    background: #e9f2ff;
    color: #1f3c88;
    font-size: 0.85rem;
    font-weight: 600;
    margin-right: 6px;
    margin-bottom: 6px;
}
.small-muted {
    color: #777;
    font-size: 0.92rem;
}
.ho-box {
    background: #fff8e7;
    border: 1px solid #f1dca7;
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 12px;
}
.ho-title {
    font-size: 1.1rem;
    font-weight: 800;
    color: #8a5a00;
    margin-bottom: 6px;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">초등학교 6학년 학습자 유형 분석 웹앱</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">4가지 검사결과를 종합하여 인지적·정의적·사회적 특성을 분석하고, 학습자 특성에 맞는 창작형 호(號) 3가지를 추천합니다.</div>', unsafe_allow_html=True)

# -----------------------------------
# PDF 텍스트 추출
# -----------------------------------
def extract_text_pdfplumber(uploaded_file):
    text_all = []
    try:
        uploaded_file.seek(0)
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                if text.strip():
                    text_all.append(text)
        return "\n".join(text_all), None
    except Exception as e:
        return "", str(e)

def extract_text_pypdf(uploaded_file):
    if PdfReader is None:
        return "", "pypdf 사용 불가"
    try:
        uploaded_file.seek(0)
        reader = PdfReader(uploaded_file)
        texts = []
        for page in reader.pages:
            try:
                t = page.extract_text() or ""
                if t.strip():
                    texts.append(t)
            except Exception:
                continue
        return "\n".join(texts), None
    except Exception as e:
        return "", str(e)

def extract_text_from_pdf(uploaded_file):
    text1, err1 = extract_text_pdfplumber(uploaded_file)
    text2, err2 = extract_text_pypdf(uploaded_file)

    combined = "\n".join([t for t in [text1, text2] if t and t.strip()]).strip()

    debug = {
        "pdfplumber_error": err1,
        "pypdf_error": err2,
        "pdfplumber_len": len(text1 or ""),
        "pypdf_len": len(text2 or ""),
        "combined_len": len(combined or "")
    }
    return combined, debug

# -----------------------------------
# 점수 변환
# -----------------------------------
def level_score(v):
    mapping = {
        "미도달": 1,
        "기초": 2,
        "보통": 3,
        "도달": 4,
        "우수": 5,
        "낮음": 2,
        "중간": 3,
        "높음": 5
    }
    return mapping.get(v, 3)

# -----------------------------------
# 파싱 함수
# -----------------------------------
def parse_career_pdf(text):
    result = {
        "type_code": None,
        "scores": {},
        "summary": [],
        "detected": False
    }

    patterns = [
        r"대표적인 흥미유형은\s*([A-Z]-[A-Z])형",
        r"검사자님의 흥미유형은\s*([A-Z]-[A-Z])\s*입니다",
        r"흥미유형은\s*([A-Z]-[A-Z])\s*입니다",
        r"([A-Z]-[A-Z])\s*형"
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            result["type_code"] = m.group(1)
            result["detected"] = True
            break

    score_pattern = re.search(
        r"R$현실형$\s*I$탐구형$\s*A$예술형$\s*S$사회형$\s*E$진취형$\s*C$관습형$\s*([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)",
        text,
        re.DOTALL
    )
    if score_pattern:
        result["scores"] = {
            "R": float(score_pattern.group(1)),
            "I": float(score_pattern.group(2)),
            "A": float(score_pattern.group(3)),
            "S": float(score_pattern.group(4)),
            "E": float(score_pattern.group(5)),
            "C": float(score_pattern.group(6))
        }
        result["detected"] = True
    else:
        fallback = re.search(r"(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)", text)
        if fallback:
            result["scores"] = {
                "R": float(fallback.group(1)),
                "I": float(fallback.group(2)),
                "A": float(fallback.group(3)),
                "S": float(fallback.group(4)),
                "E": float(fallback.group(5)),
                "C": float(fallback.group(6))
            }

    type_code = result["type_code"]
    if type_code == "S-C":
        result["summary"] = [
            "사람과의 관계, 공감, 도움 행동에 강점을 보일 가능성이 있습니다.",
            "규칙과 책임감을 중시하고 꼼꼼하게 과제를 수행하려는 경향이 있습니다."
        ]
    elif type_code:
        result["summary"] = [f"{type_code}형 특성은 향후 규칙 확장을 통해 더 정밀하게 해석할 수 있습니다."]

    return result

def parse_basic_pdf(text):
    result = {
        "detected_keywords": [],
        "raw_hint": None
    }
    keywords = ["국어", "수학", "읽기", "쓰기", "수리", "기초학력", "진단"]
    found = [k for k in keywords if k in text]
    result["detected_keywords"] = found
    if found:
        result["raw_hint"] = "일부 핵심 키워드가 감지되었습니다."
    return result

def parse_learning_type_pdf(text):
    result = {
        "detected": False,
        "keywords": [],
        "summary": []
    }
    keywords = ["자기주도", "집중", "학습", "계획", "과제", "습관", "동기"]
    found = [k for k in keywords if k in text]
    result["keywords"] = found
    if found:
        result["detected"] = True
        result["summary"].append("학습유형검사 PDF에서 일부 학습 관련 키워드가 확인되었습니다.")
    return result

def parse_social_emotional_pdf(text):
    result = {
        "detected": False,
        "keywords": [],
        "summary": []
    }
    keywords = ["자기인식", "자기조절", "공감", "관계", "협력", "의사소통", "사회정서"]
    found = [k for k in keywords if k in text]
    result["keywords"] = found
    if found:
        result["detected"] = True
        result["summary"].append("사회정서역량검사 PDF에서 일부 사회정서 관련 키워드가 확인되었습니다.")
    return result

# -----------------------------------
# 호 추천
# -----------------------------------
def recommend_ho(cognitive_score, affective_score, social_score, learning_style, social_subscores):
    candidates = []

    # 인지 기반
    if cognitive_score >= 80:
        candidates.extend([
            ("사유", "깊이 생각하고 이해를 넓혀 가는 힘을 담은 호"),
            ("온결", "차분하고 단정하게 배움을 정리해 나가는 모습을 담은 호"),
            ("지음", "앎을 쌓고 자기만의 배움을 만들어 가는 뜻을 담은 호"),
        ])
    elif cognitive_score >= 60:
        candidates.extend([
            ("다봄", "배움을 넓게 보고 차근차근 성장해 가는 뜻을 담은 호"),
            ("새결", "새롭게 이해하고 스스로 길을 만들어 가는 의미의 호"),
            ("고운", "차분하고 반듯하게 배움을 이어 가는 기질을 담은 호"),
        ])
    else:
        candidates.extend([
            ("정진", "조금씩 꾸준히 앞으로 나아가는 힘을 담은 호"),
            ("한걸", "한 걸음씩 성실하게 성장해 가는 뜻을 담은 호"),
            ("새봄", "지금부터 다시 힘차게 자라나는 가능성을 담은 호"),
        ])

    # 정의적 기반
    if affective_score >= 80:
        candidates.extend([
            ("온빛", "따뜻한 마음과 밝은 에너지를 함께 지닌 모습을 담은 호"),
            ("다온", "좋은 기운이 주변에 널리 퍼지는 뜻을 담은 호"),
            ("마루", "스스로 중심을 잡고 단단히 서는 의미의 호"),
        ])
    elif affective_score >= 60:
        candidates.extend([
            ("누리", "넓게 배우고 바르게 자라는 가능성을 담은 호"),
            ("이룸", "노력으로 배움을 이루어 가는 의미를 담은 호"),
            ("가온", "중심을 잡고 조화롭게 성장하는 뜻의 호"),
        ])
    else:
        candidates.extend([
            ("온새", "따뜻한 지지 속에서 새롭게 피어나는 가능성을 담은 호"),
            ("한빛", "작지만 분명한 빛을 키워 가는 의미의 호"),
            ("다움", "자기다운 속도로 성장해 가는 뜻을 담은 호"),
        ])

    # 사회 기반
    if social_score >= 80:
        candidates.extend([
            ("온화", "따뜻하고 부드럽게 사람을 품는 성품을 담은 호"),
            ("늘품", "주변과 함께 자라며 품을 넓혀 가는 뜻의 호"),
            ("이음", "사람과 사람을 이어 주는 힘을 담은 호"),
        ])
    elif social_score >= 60:
        candidates.extend([
            ("다정", "친절하고 다정하게 관계를 맺는 모습을 담은 호"),
            ("어진", "바르고 너그러운 마음을 지닌 뜻의 호"),
            ("한결", "꾸준하고 반듯하게 관계를 이어 가는 의미의 호"),
        ])
    else:
        candidates.extend([
            ("고운", "부드럽고 고운 마음을 천천히 키워 가는 뜻의 호"),
            ("온결", "관계를 차분하게 맺으며 마음결을 다듬는 의미의 호"),
            ("새온", "새롭게 마음을 열고 관계를 넓혀 가는 뜻의 호"),
        ])

    # 학습유형 보정
    if learning_style == "시각형":
        candidates.append(("새봄", "이미지와 흐름을 통해 새롭게 이해를 넓혀 가는 뜻의 호"))
    elif learning_style == "청각형":
        candidates.append(("다울", "듣고 나누며 자기다운 배움을 만들어 가는 뜻의 호"))
    elif learning_style == "활동형":
        candidates.append(("바름", "움직이며 익히고 실천하며 성장하는 뜻의 호"))

    # 사회정서 보정
    empathy = social_subscores.get("공감", 3)
    relation = social_subscores.get("관계형성", 3)
    if empathy >= 4 and relation >= 4:
        candidates.append(("온마음", "타인의 마음을 살피고 관계를 따뜻하게 잇는 뜻의 호"))

    # 중복 제거
    seen = set()
    final = []
    for name, desc in candidates:
        if name not in seen:
            seen.add(name)
            final.append({"name": name, "meaning": desc})
        if len(final) == 3:
            break

    return final

# -----------------------------------
# 분석 함수
# -----------------------------------
def compute_domain_scores(career_result, basic_scores, learning_subscores, social_subscores):
    basic_numeric = {k: level_score(v) for k, v in basic_scores.items()}
    avg_basic = sum(basic_numeric.values()) / len(basic_numeric)

    learning_vals = list(learning_subscores.values())
    social_vals = list(social_subscores.values())

    holland = career_result.get("scores", {})
    s_score = holland.get("S", 50)
    c_score = holland.get("C", 50)

    cognitive = round(((avg_basic / 5) * 70) + ((sum(learning_vals) / (len(learning_vals) * 5)) * 30), 1)
    affective = round((((sum(learning_vals) / (len(learning_vals) * 5)) * 50) + ((sum(social_vals) / (len(social_vals) * 5)) * 30) + (((c_score + s_score) / 140) * 20)) * 100, 1)
    social = round((((sum(social_vals) / (len(social_vals) * 5)) * 70) + ((s_score / 70) * 30)) * 100, 1)

    cognitive = min(cognitive, 100)
    affective = min(affective, 100)
    social = min(social, 100)

    return {
        "인지적 특성": cognitive,
        "정의적 특성": affective,
        "사회적 특성": social
    }

def analyze_learner(student, career_result, basic_scores, learning_style, learning_subscores, social_subscores):
    cognitive = []
    affective = []
    social = []
    strengths = []
    needs = []
    recommendations = []

    basic_numeric = {k: level_score(v) for k, v in basic_scores.items()}
    avg_basic = sum(basic_numeric.values()) / len(basic_numeric)
    low_areas = [k for k, v in basic_scores.items() if v in ["미도달", "기초", "낮음"]]
    high_areas = [k for k, v in basic_scores.items() if v in ["우수", "도달", "높음"]]

    self_direction = learning_subscores["자기주도성"]
    concentration = learning_subscores["집중지속"]
    task_attitude = learning_subscores["과제수행"]
    motivation = learning_subscores["학습동기"]

    self_awareness = social_subscores["자기인식"]
    self_control = social_subscores["자기조절"]
    empathy = social_subscores["공감"]
    relation = social_subscores["관계형성"]
    cooperation = social_subscores["협력"]

    holland_scores = career_result.get("scores", {})
    type_code = career_result.get("type_code")
    s_score = holland_scores.get("S", 0)
    c_score = holland_scores.get("C", 0)

    # 인지적
    if avg_basic >= 4.0:
        cognitive.append("기초학습 능력이 전반적으로 안정적이며, 학습 내용을 확장해 나갈 가능성이 높습니다.")
        strengths.append("기초학습의 안정성이 비교적 높습니다.")
    elif avg_basic >= 3.0:
        cognitive.append("기초학습 수준은 전반적으로 보통이며, 영역별 편차를 고려한 지도가 필요합니다.")
    else:
        cognitive.append("기초학습의 여러 영역에서 보완이 필요하며, 단계적 설명과 반복 연습이 중요합니다.")
        needs.append("기초학습 보완이 필요합니다.")

    if low_areas:
        cognitive.append(f"특히 {', '.join(low_areas)} 영역은 우선 지원 대상으로 볼 수 있습니다.")
        recommendations.append(f"{', '.join(low_areas)} 영역은 짧고 반복적인 학습 과제로 재구성하는 것이 좋습니다.")
    if high_areas:
        cognitive.append(f"{', '.join(high_areas)} 영역은 비교적 안정적으로 수행할 가능성이 있습니다.")

    if self_direction >= 4:
        cognitive.append("자기주도성이 비교적 높아 스스로 계획하고 실천하는 활동에 잘 반응할 수 있습니다.")
        strengths.append("자기주도적 학습 역량이 비교적 좋습니다.")
    if concentration <= 2:
        cognitive.append("집중 지속 시간이 짧을 수 있어 학습 단위를 짧게 나누는 것이 효과적일 수 있습니다.")
        needs.append("집중 지속을 돕는 구조화가 필요할 수 있습니다.")
    if learning_style == "시각형":
        cognitive.append("시각 자료, 도식, 색 구분, 이미지 기반 자료에서 이해가 높아질 가능성이 있습니다.")
    elif learning_style == "청각형":
        cognitive.append("설명 듣기, 말로 정리하기, 질의응답 방식에서 학습 효율이 높아질 수 있습니다.")
    elif learning_style == "활동형":
        cognitive.append("직접 해보기, 조작 활동, 움직임이 포함된 과제에서 이해가 높아질 수 있습니다.")

    if c_score >= 55:
        cognitive.append("절차와 규칙에 따라 차근차근 학습하는 방식에 강점을 보일 수 있습니다.")
        strengths.append("체계적이고 절차적인 활동에 잘 적응할 가능성이 있습니다.")

    # 정의적
    if motivation >= 4 and task_attitude >= 4:
        affective.append("학습 동기와 과제 태도가 안정적이어서 꾸준한 학습 참여가 기대됩니다.")
        strengths.append("학습 동기와 과제 수행 태도가 비교적 좋습니다.")
    elif motivation <= 2:
        affective.append("학습 동기가 낮아 보일 수 있어 관심과 성공 경험을 연결하는 접근이 필요합니다.")
        needs.append("학습 동기 향상을 위한 지원이 필요할 수 있습니다.")

    if self_awareness >= 4:
        affective.append("자신의 감정과 상태를 비교적 잘 인식하며, 피드백을 받아들이는 힘이 있을 수 있습니다.")
    if self_control >= 4:
        affective.append("정서 조절과 자기 통제가 비교적 안정적일 가능성이 있습니다.")
        strengths.append("자기조절 역량이 비교적 좋습니다.")
    elif self_control <= 2:
        affective.append("감정이나 스트레스 상황에서 흔들릴 수 있어 정서적 안전감 형성이 중요합니다.")
        needs.append("정서 조절을 돕는 지원이 필요할 수 있습니다.")

    if type_code == "S-C":
        affective.append("사람과의 관계를 중요하게 여기며, 인정과 지지를 받을 때 학습 동기가 높아질 가능성이 있습니다.")
        affective.append("성실성과 책임감을 기반으로 과제를 수행하려는 경향이 나타날 수 있습니다.")

    # 사회적
    if empathy >= 4 and relation >= 4 and cooperation >= 4:
        social.append("공감, 관계 형성, 협력 측면에서 강점을 보일 가능성이 큽니다.")
        strengths.append("또래와의 협력 및 관계 맺기에서 강점이 있을 수 있습니다.")
    elif empathy <= 2 or relation <= 2:
        social.append("또래 관계나 공감 표현에서 조심스러운 모습이 있을 수 있어 구조화된 관계 활동이 도움이 됩니다.")
        needs.append("사회적 상호작용을 돕는 구조화된 경험이 필요할 수 있습니다.")

    if s_score >= 57:
        social.append("진로흥미유형 결과를 보면 사람 중심의 상호작용과 협력 활동에 긍정적으로 반응할 가능성이 있습니다.")
    if c_score >= 55:
        social.append("학급 규칙과 질서를 잘 따르며, 맡은 역할을 책임감 있게 수행할 가능성이 있습니다.")
    if cooperation >= 4:
        social.append("모둠활동이나 공동 과제에서 역할을 맡아 성실하게 참여할 수 있습니다.")

    # 지도 제안
    recommendations.append("강점을 먼저 확인한 뒤 보완이 필요한 영역을 작게 나누어 지도하는 것이 좋습니다.")
    if learning_style == "시각형":
        recommendations.append("마인드맵, 그림, 표, 색 구분 자료를 적극 활용해 주세요.")
    elif learning_style == "청각형":
        recommendations.append("말로 설명하고 다시 말해보게 하는 방식의 수업 구성이 효과적일 수 있습니다.")
    elif learning_style == "활동형":
        recommendations.append("움직임, 조작, 역할 수행이 포함된 활동 중심 수업이 도움이 될 수 있습니다.")
    if empathy >= 4:
        recommendations.append("또래 도우미 역할이나 협력 과제에서 장점을 살릴 수 있도록 기회를 주세요.")
    if concentration <= 2:
        recommendations.append("과제 시간을 짧게 나누고 즉각적인 피드백을 제공해 주세요.")

    overall = []
    overall.append(f"{student['name']} 학생은 여러 검사 결과를 종합할 때, 학습 특성과 정서·사회적 특성을 함께 고려한 맞춤형 지도가 필요한 학생입니다.")
    if strengths:
        overall.append("특히 강점이 드러나는 영역을 먼저 살려 주면 학습 자신감과 참여도를 높이는 데 도움이 됩니다.")
    if needs:
        overall.append("보완이 필요한 영역은 한 번에 크게 요구하기보다 작은 목표로 나누어 접근하는 것이 효과적입니다.")

    return {
        "인지적 특성": cognitive,
        "정의적 특성": affective,
        "사회적 특성": social,
        "강점": strengths,
        "지원 필요": needs,
        "지도 제안": recommendations,
        "종합 의견": overall
    }

def make_download_data(student, career_result, basic_scores, learning_style, learning_subscores, social_subscores, analysis, domain_scores, ho_result):
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "student": student,
        "career_result": career_result,
        "basic_scores": basic_scores,
        "learning_style": learning_style,
        "learning_subscores": learning_subscores,
        "social_subscores": social_subscores,
        "domain_scores": domain_scores,
        "analysis": analysis,
        "recommended_ho": ho_result
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

def render_plotly_bar(df, x, y, color=None, title="", y_max=None):
    fig = px.bar(
        df,
        x=x,
        y=y,
        color=color if color else x,
        text=y,
        title=title
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        height=400,
        showlegend=False,
        xaxis_title="",
        yaxis_title="점수",
        margin=dict(l=20, r=20, t=60, b=20)
    )
    if y_max:
        fig.update_yaxes(range=[0, y_max])
    return fig

# -----------------------------------
# 사이드바
# -----------------------------------
with st.sidebar:
    st.header("입력 정보")

    student_name = st.text_input("학생 이름", value="홍길동")
    student_grade = st.selectbox("학년", [6], index=0)
    student_class = st.text_input("반", value="1")
    student_number = st.text_input("번호", value="1")

    st.markdown("---")
    st.subheader("PDF 업로드 4종")
    career_pdf = st.file_uploader("1) 진로탐색유형검사 PDF", type=["pdf"])
    basic_pdf = st.file_uploader("2) 기초학력진단검사 PDF", type=["pdf"])
    learning_pdf = st.file_uploader("3) 학습유형검사 PDF", type=["pdf"])
    social_pdf = st.file_uploader("4) 사회정서역량검사 PDF", type=["pdf"])

    st.markdown("---")
    st.subheader("기초학력 수동 입력")
    korean = st.selectbox("국어", ["미도달", "기초", "보통", "도달", "우수"], index=2)
    math = st.selectbox("수학", ["미도달", "기초", "보통", "도달", "우수"], index=2)
    reading = st.selectbox("읽기", ["미도달", "기초", "보통", "도달", "우수"], index=2)
    writing = st.selectbox("쓰기", ["미도달", "기초", "보통", "도달", "우수"], index=2)
    numeracy = st.selectbox("수리", ["미도달", "기초", "보통", "도달", "우수"], index=2)

    st.markdown("---")
    st.subheader("학습유형 수동 입력")
    learning_style = st.selectbox("선호 학습 방식", ["시각형", "청각형", "활동형", "복합형"], index=3)
    self_direction = st.slider("자기주도성", 1, 5, 3)
    concentration = st.slider("집중지속", 1, 5, 3)
    task_attitude = st.slider("과제수행", 1, 5, 3)
    motivation = st.slider("학습동기", 1, 5, 3)

    st.markdown("---")
    st.subheader("사회정서역량 수동 입력")
    self_awareness = st.slider("자기인식", 1, 5, 3)
    self_control = st.slider("자기조절", 1, 5, 3)
    empathy = st.slider("공감", 1, 5, 3)
    relation = st.slider("관계형성", 1, 5, 3)
    cooperation = st.slider("협력", 1, 5, 3)

    analyze_btn = st.button("분석 실행", use_container_width=True)

student = {
    "name": student_name,
    "grade": student_grade,
    "class": student_class,
    "number": student_number
}

basic_scores = {
    "국어": korean,
    "수학": math,
    "읽기": reading,
    "쓰기": writing,
    "수리": numeracy
}

learning_subscores = {
    "자기주도성": self_direction,
    "집중지속": concentration,
    "과제수행": task_attitude,
    "학습동기": motivation
}

social_subscores = {
    "자기인식": self_awareness,
    "자기조절": self_control,
    "공감": empathy,
    "관계형성": relation,
    "협력": cooperation
}

career_result = {"type_code": None, "scores": {}, "summary": [], "detected": False}
basic_result = {}
learning_result = {}
social_result = {}

# -----------------------------------
# 상단 카드
# -----------------------------------
a, b, c = st.columns(3)
with a:
    st.markdown(f"""
    <div class="card">
        <div class="card-title">학생 정보</div>
        <div><b>{student['name']}</b> / {student['grade']}학년 {student['class']}반 {student['number']}번</div>
    </div>
    """, unsafe_allow_html=True)

with b:
    st.markdown("""
    <div class="card">
        <div class="card-title">분석 자료</div>
        <span class="badge">진로탐색유형</span>
        <span class="badge">기초학력</span>
        <span class="badge">학습유형</span>
        <span class="badge">사회정서역량</span>
    </div>
    """, unsafe_allow_html=True)

with c:
    st.markdown("""
    <div class="card">
        <div class="card-title">결과 제공</div>
        <div class="small-muted">3영역 분석, 차트 시각화, 강점/지원 필요/지도 제안, 창작형 호(號) 추천 3종</div>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------
# PDF 분석 섹션
# -----------------------------------
st.markdown("## 1. PDF 업로드 결과 확인")

col1, col2 = st.columns(2)
col3, col4 = st.columns(2)

with col1:
    st.markdown('<div class="card"><div class="card-title">진로탐색유형검사 PDF</div>', unsafe_allow_html=True)
    if career_pdf:
        text, debug = extract_text_from_pdf(career_pdf)
        career_result = parse_career_pdf(text)
        if career_result["detected"]:
            st.success("진로탐색유형검사 결과를 인식했습니다.")
        else:
            st.warning("자동 인식이 완전하지 않습니다.")
        st.write(debug)
        if career_result["type_code"]:
            st.write(f"**대표 유형:** {career_result['type_code']}")
        if career_result["scores"]:
            st.dataframe(pd.DataFrame({
                "유형": list(career_result["scores"].keys()),
                "점수": list(career_result["scores"].values())
            }), hide_index=True, use_container_width=True)
        with st.expander("추출 텍스트 보기"):
            st.text_area("career_text", text[:2000], height=180, label_visibility="collapsed")
    else:
        st.info("PDF를 업로드해 주세요.")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card"><div class="card-title">기초학력진단검사 PDF</div>', unsafe_allow_html=True)
    if basic_pdf:
        text, debug = extract_text_from_pdf(basic_pdf)
        basic_result = parse_basic_pdf(text)
        if text.strip():
            st.success("PDF에서 텍스트를 추출했습니다.")
        else:
            st.warning("텍스트 추출이 충분하지 않습니다. 수동 입력값을 함께 활용하세요.")
        st.write(debug)
        if basic_result.get("detected_keywords"):
            st.write("**감지 키워드:**", ", ".join(basic_result["detected_keywords"]))
        with st.expander("추출 텍스트 보기"):
            st.text_area("basic_text", text[:2000], height=180, label_visibility="collapsed")
    else:
        st.info("PDF를 업로드해 주세요.")
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="card"><div class="card-title">학습유형검사 PDF</div>', unsafe_allow_html=True)
    if learning_pdf:
        text, debug = extract_text_from_pdf(learning_pdf)
        learning_result = parse_learning_type_pdf(text)
        if text.strip():
            st.success("PDF에서 텍스트를 추출했습니다.")
        else:
            st.warning("텍스트 추출이 충분하지 않습니다. 수동 입력값을 함께 활용하세요.")
        st.write(debug)
        if learning_result.get("keywords"):
            st.write("**감지 키워드:**", ", ".join(learning_result["keywords"]))
        with st.expander("추출 텍스트 보기"):
            st.text_area("learning_text", text[:2000], height=180, label_visibility="collapsed")
    else:
        st.info("PDF를 업로드해 주세요.")
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    st.markdown('<div class="card"><div class="card-title">사회정서역량검사 PDF</div>', unsafe_allow_html=True)
    if social_pdf:
        text, debug = extract_text_from_pdf(social_pdf)
        social_result = parse_social_emotional_pdf(text)
        if text.strip():
            st.success("PDF에서 텍스트를 추출했습니다.")
        else:
            st.warning("텍스트 추출이 충분하지 않습니다. 수동 입력값을 함께 활용하세요.")
        st.write(debug)
        if social_result.get("keywords"):
            st.write("**감지 키워드:**", ", ".join(social_result["keywords"]))
        with st.expander("추출 텍스트 보기"):
            st.text_area("social_text", text[:2000], height=180, label_visibility="collapsed")
    else:
        st.info("PDF를 업로드해 주세요.")
    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------
# 입력값 시각화
# -----------------------------------
st.markdown("## 2. 입력값 시각화")

v1, v2, v3 = st.columns(3)

with v1:
    basic_df = pd.DataFrame({
        "영역": list(basic_scores.keys()),
        "점수": [level_score(v) for v in basic_scores.values()]
    })
    fig_basic = render_plotly_bar(basic_df, x="영역", y="점수", title="기초학력 수준", y_max=5)
    st.plotly_chart(fig_basic, use_container_width=True)

with v2:
    learning_df = pd.DataFrame({
        "영역": list(learning_subscores.keys()),
        "점수": list(learning_subscores.values())
    })
    fig_learning = render_plotly_bar(learning_df, x="영역", y="점수", title="학습유형 하위 점수", y_max=5)
    st.plotly_chart(fig_learning, use_container_width=True)

with v3:
    social_df = pd.DataFrame({
        "영역": list(social_subscores.keys()),
        "점수": list(social_subscores.values())
    })
    fig_social = render_plotly_bar(social_df, x="영역", y="점수", title="사회정서역량 하위 점수", y_max=5)
    st.plotly_chart(fig_social, use_container_width=True)

if career_result.get("scores"):
    st.markdown("### 진로탐색유형(RIASEC) 점수")
    career_df = pd.DataFrame({
        "유형": list(career_result["scores"].keys()),
        "점수": list(career_result["scores"].values())
    })
    fig_career = render_plotly_bar(career_df, x="유형", y="점수", title="Holland(RIASEC) 점수")
    st.plotly_chart(fig_career, use_container_width=True)

# -----------------------------------
# 분석 실행
# -----------------------------------
if analyze_btn:
    domain_scores = compute_domain_scores(
        career_result,
        basic_scores,
        learning_subscores,
        social_subscores
    )

    analysis = analyze_learner(
        student,
        career_result,
        basic_scores,
        learning_style,
        learning_subscores,
        social_subscores
    )

    ho_result = recommend_ho(
        domain_scores["인지적 특성"],
        domain_scores["정의적 특성"],
        domain_scores["사회적 특성"],
        learning_style,
        social_subscores
    )

    st.markdown("## 3. 3영역 요약 점수")
    domain_df = pd.DataFrame({
        "영역": list(domain_scores.keys()),
        "점수": list(domain_scores.values())
    })
    fig_domain = render_plotly_bar(domain_df, x="영역", y="점수", title="인지적·정의적·사회적 특성 요약 점수", y_max=100)
    st.plotly_chart(fig_domain, use_container_width=True)

    st.markdown("## 4. 학습자 특성 분석")
    tab1, tab2, tab3, tab4 = st.tabs(["인지적 특성", "정의적 특성", "사회적 특성", "종합 보고"])

    with tab1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        for item in analysis["인지적 특성"]:
            st.write(f"- {item}")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        for item in analysis["정의적 특성"]:
            st.write(f"- {item}")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        for item in analysis["사회적 특성"]:
            st.write(f"- {item}")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab4:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="card"><div class="card-title">강점</div>', unsafe_allow_html=True)
            if analysis["강점"]:
                for item in analysis["강점"]:
                    st.write(f"- {item}")
            else:
                st.write("- 현재 자료만으로는 강점을 더 구체화하려면 추가 관찰이 필요합니다.")
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="card"><div class="card-title">지원 필요</div>', unsafe_allow_html=True)
            if analysis["지원 필요"]:
                for item in analysis["지원 필요"]:
                    st.write(f"- {item}")
            else:
                st.write("- 현재 자료 기준으로 즉각적인 위험 요인은 크지 않습니다.")
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="card"><div class="card-title">지도 제안</div>', unsafe_allow_html=True)
            for item in analysis["지도 제안"]:
                st.write(f"- {item}")
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="card"><div class="card-title">종합 의견</div>', unsafe_allow_html=True)
            for item in analysis["종합 의견"]:
                st.write(f"- {item}")
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("## 5. 학습자에게 어울리는 창작형 호(號) 추천")
    for idx, ho in enumerate(ho_result, start=1):
        st.markdown(f"""
        <div class="ho-box">
            <div class="ho-title">{idx}. {ho['name']}</div>
            <div>{ho['meaning']}</div>
        </div>
        """, unsafe_allow_html=True)

    json_data = make_download_data(
        student,
        career_result,
        basic_scores,
        learning_style,
        learning_subscores,
        social_subscores,
        analysis,
        domain_scores,
        ho_result
    )

    st.download_button(
        label="분석 결과 JSON 다운로드",
        data=json_data,
        file_name=f"{student['name']}_학습자유형분석_전체수정본.json",
        mime="application/json",
        use_container_width=True
    )

else:
    st.info("왼쪽 사이드바에서 입력값을 설정한 뒤 **분석 실행** 버튼을 눌러 주세요.")
