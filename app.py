import streamlit as st
import google.generativeai as genai
import json
from fpdf import FPDF
from PIL import Image
import io
import os

# 페이지 설정
st.set_page_config(page_title="동백 성 요셉 성당 전례 자동화", layout="wide")
st.title("🕊️ 전례 기도문 & 일정표 자동 생성기")
st.markdown("수기 당번표와 기도문 이미지를 업로드하면 제미나이가 자동으로 문서를 만들어줍니다. 화면에서 내용을 수정한 후 PDF로 다운로드하세요!")

# --- 1. API 키 설정 (사이드바) ---
with st.sidebar:
    st.header("⚙️ 설정")
    api_key = st.text_input("Gemini API Key를 입력하세요", type="password")
    if api_key:
        genai.configure(api_key=api_key)
    st.markdown("[API 키 발급받기(무료)](https://aistudio.google.com/app/apikey)")

# --- PDF 생성 함수 (fpdf2 사용) ---
def create_pdf(schedule_data, prayer_data, selected_date, font_path="NanumGothic.ttf"):
    pdf = FPDF()
    # 한글 폰트 추가 (동일 폴더에 NanumGothic.ttf 필요)
    pdf.add_font("Nanum", "", font_path, uni=True)
    pdf.add_page()
    pdf.set_font("Nanum", "", 12)
    
    # 해당 날짜의 담당자 찾기
    officials = next((item for item in schedule_data if item["날짜"] == selected_date), None)
    
    if not officials:
        pdf.cell(200, 10, txt="선택한 날짜의 담당자 정보가 없습니다.", ln=True, align='C')
        return pdf.output(dest='S').encode('latin-1')

    # 타이틀
    pdf.set_font("Nanum", "", 16)
    pdf.cell(200, 10, txt=f"동백 성 요셉 성당 초등 전례부 ({selected_date})", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Nanum", "", 12)
    
    # 해설 (입당 전 텍스트만 사용)
    pdf.multi_cell(0, 8, txt=f"[해설: {officials.get('해설', '')}]")
    pdf.multi_cell(0, 8, txt=prayer_data.get('입당전', ''))
    pdf.ln(5)
    
    # 보편지향기도 1~4
    for i in range(1, 5):
        key = str(i)
        pdf.multi_cell(0, 8, txt=f"[보편지향기도 {key}: {officials.get(f'기도{key}', '')}]")
        pdf.multi_cell(0, 8, txt=prayer_data.get(f'기도{key}', ''))
        pdf.ln(5)
        
    return pdf.output(dest='S').encode('latin-1')

# --- 2. 파일 업로드 ---
col1, col2 = st.columns(2)
with col1:
    schedule_file = st.file_uploader("1. 수기 당번표 이미지 (파일 3)", type=["jpg", "png", "jpeg"])
with col2:
    prayer_file = st.file_uploader("2. 기도문 이미지 (파일 2)", type=["jpg", "png", "jpeg"])

# --- 3. 데이터 추출 및 수정 ---
if schedule_file and prayer_file:
    if not api_key:
        st.warning("👈 사이드바에 Gemini API Key를 입력해주세요.")
    else:
        if st.button("🚀 AI 데이터 추출 시작", type="primary"):
            with st.spinner("제미나이가 이미지를 읽고 있습니다... (약 10초 소요)"):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash-latest')
                    
                    # 수기 당번표 분석
                    img_schedule = Image.open(schedule_file)
                    prompt_schedule = """
                    이 이미지는 성당 전례 수기 일정표입니다.
                    날짜별로 '해설', '제1독서', 보편지향기도 '1', '2', '3', '4' 담당자 이름을 추출하여 아래 형식의 JSON 배열로만 응답하세요. (마크다운 없이)
                    [{"날짜": "8.2", "해설": "남윤찬", "제1독서": "기승민", "기도1": "이제인", "기도2": "...", "기도3": "...", "기도4": "..."}]
                    """
                    resp_schedule = model.generate_content([img_schedule, prompt_schedule])
                    schedule_text = resp_schedule.text.strip().replace("```json", "").replace("```", "")
                    st.session_state['schedule_data'] = json.loads(schedule_text)
                    
                    # 기도문 분석
                    img_prayer = Image.open(prayer_file)
                    prompt_prayer = """
                    이 이미지는 기도문입니다.
                    '입당 전' 텍스트 전체와 '보편 지향 기도' 1, 2, 3, 4 항목 텍스트를 추출하여 아래 JSON으로만 응답하세요.
                    {"입당전": "텍스트...", "기도1": "텍스트...", "기도2": "텍스트...", "기도3": "텍스트...", "기도4": "텍스트..."}
                    """
                    resp_prayer = model.generate_content([img_prayer, prompt_prayer])
                    prayer_text = resp_prayer.text.strip().replace("```json", "").replace("```", "")
                    st.session_state['prayer_data'] = json.loads(prayer_text)
                    
                    st.success("데이터 추출 성공! 아래에서 내용을 확인하고 수정하세요.")
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")

# --- 4. 사용자 웹페이지 수정 화면 ---
if 'schedule_data' in st.session_state and 'prayer_data' in st.session_state:
    st.divider()
    st.subheader("📝 추출된 데이터 수정 (클릭하여 텍스트 수정 가능)")
    
    # 당번표 표(Table) 에디터 ('전례일정_7월.pdf' 양식에 해당)
    st.markdown("**담당자 배정표 (파일 4 양식)**")
    edited_schedule = st.data_editor(st.session_state['schedule_data'], num_rows="dynamic")
    
    # 기도문 텍스트 에디터
    st.markdown("**기도문 텍스트**")
    edited_prayer = {}
    edited_prayer['입당전'] = st.text_area("'해설' 칸에 들어갈 입당 전 텍스트", value=st.session_state['prayer_data'].get('입당전', ''), height=100)
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        edited_prayer['기도1'] = st.text_area("보편지향기도 1", value=st.session_state['prayer_data'].get('기도1', ''), height=100)
        edited_prayer['기도3'] = st.text_area("보편지향기도 3", value=st.session_state['prayer_data'].get('기도3', ''), height=100)
    with col_p2:
        edited_prayer['기도2'] = st.text_area("보편지향기도 2", value=st.session_state['prayer_data'].get('기도2', ''), height=100)
        edited_prayer['기도4'] = st.text_area("보편지향기도 4", value=st.session_state['prayer_data'].get('기도4', ''), height=100)

    # --- 5. 최종 문서(PDF) 다운로드 ---
    st.divider()
    st.subheader("📥 최종 PDF 다운로드")
    
    date_list = [item['날짜'] for item in edited_schedule]
    selected_date = st.selectbox("어느 날짜의 주보(파일 1)를 생성할까요?", date_list)
    
    # 한글 폰트(NanumGothic.ttf)가 코드와 같은 폴더에 있어야 PDF가 정상적으로 만들어집니다.
    if st.button("문서 생성 및 다운로드 준비"):
        try:
            pdf_bytes = create_pdf(edited_schedule, edited_prayer, selected_date)
            st.download_button(
                label="📄 '파일 1' 양식 PDF 다운로드",
                data=pdf_bytes,
                file_name=f"{selected_date}_전례문.pdf",
                mime="application/pdf"
            )
        except RuntimeError as e:
            st.error("⚠️ 폰트 파일 오류: 'NanumGothic.ttf' 폰트 파일이 폴더에 있는지 확인해주세요.")
