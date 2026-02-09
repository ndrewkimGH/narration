import streamlit as st
import asyncio
import edge_tts
import os
from pydub import AudioSegment
import io

# --- 설정 및 데이터 ---
VOICES = {
    "한국어 여성 (선희)": "ko-KR-SunHiNeural",
    "한국어 남성 (인준)": "ko-KR-InJunNeural",
    "영어 여성 (에바)": "en-US-AvaNeural",
    "영어 남성 (가이)": "en-US-GuyNeural",
    "영어 여성 (소니아)": "en-GB-SoniaNeural"
}

# --- 핵심 로직 함수 ---
async def generate_audio_segment(text, voice, rate):
    rate_str = f"{rate:+d}%"
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    
    if not audio_data: return None
    return AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")

async def process_narration(text_data, selected_voice, speed, pause_sec, bgm_file):
    raw_lines = text_data.split('\n')
    combined = AudioSegment.empty()
    
    normal_pause = AudioSegment.silent(duration=int(pause_sec * 1000))
    paragraph_pause = AudioSegment.silent(duration=int(pause_sec * 3000))

    for line in raw_lines:
        clean_line = line.strip()
        if not clean_line:
            combined += paragraph_pause
            continue
        
        segment = await generate_audio_segment(clean_line, selected_voice, speed)
        if segment:
            combined += segment + normal_pause

    if bgm_file is not None:
        bgm = AudioSegment.from_file(bgm_file)
        bgm = bgm - 25 
        if len(bgm) < len(combined):
            bgm = bgm * (len(combined) // len(bgm) + 1)
        bgm = bgm[:len(combined)]
        combined = combined.overlay(bgm)

    return combined

# --- UI 레이아웃 ---
st.set_page_config(page_title="나레이션 스튜디오", layout="wide")
st.title("🎙️ 프리미엄 나레이션 제작기")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    chosen_voice_name = st.selectbox("성우 선택", list(VOICES.keys()))
    speed = st.slider("속도 (%)", -50, 50, 0, step=5)
    pause_time = st.slider("간격 (초)", 0.0, 5.0, 1.0, 0.5)
    bgm_upload = st.file_uploader("BGM 업로드", type=["mp3", "wav"])

# 메인 입력
text_input = st.text_area("스크립트 입력", height=400)

if st.button("제작 시작"):
    if text_input:
        with st.spinner("제작 중..."):
            try:
                # 가장 안전한 비동기 실행 방식
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                final_audio = loop.run_until_complete(process_narration(
                    text_input, VOICES[chosen_voice_name], speed, pause_time, bgm_upload
                ))
                
                buffer = io.BytesIO()
                final_audio.export(buffer, format="mp3")
                st.audio(buffer.getvalue())
                st.download_button("MP3 다운로드", buffer.getvalue(), file_name="output.mp3")
            except Exception as e:
                st.error(f"오류 발생: {e}")
