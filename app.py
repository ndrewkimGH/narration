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
    "영어 남성 (가이)": "en-US-GuyNeural"
}

# --- 핵심 로직 함수 ---
async def generate_audio_segment(text, voice, rate):
    # rate 설정 (예: +0%, -10% 등)
    rate_str = f"{rate:+d}%"
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    
    return AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")

async def process_project(text_data, ko_voice, en_voice, speed, pause_sec, bgm_file):
    lines = [line.strip() for line in text_data.split('\n') if line.strip()]
    combined = AudioSegment.empty()
    pause = AudioSegment.silent(duration=int(pause_sec * 1000)) # ms 단위

    for i, line in enumerate(lines):
        voice = ko_voice if i % 2 == 0 else en_voice
        segment = await generate_audio_segment(line, voice, speed)
        combined += segment + pause

    # BGM 합성
    if bgm_file is not None:
        bgm = AudioSegment.from_file(bgm_file)
        # BGM 볼륨 낮추기 (-20dB) 및 루프(반복)
        bgm = bgm - 20 
        if len(bgm) < len(combined):
            bgm = bgm * (len(combined) // len(bgm) + 1)
        bgm = bgm[:len(combined)]
        combined = combined.overlay(bgm)

    return combined

# --- UI 레이아웃 ---
st.set_page_config(page_title="프리미엄 성경 낭독기", layout="wide")
st.title("🎙️ 프리미엄 한-영 성경 오디오 제작기")

with st.sidebar:
    st.header("⚙️ 세부 설정")
    ko_v = st.selectbox("한국어 성우", list(VOICES.keys()), index=0)
    en_v = st.selectbox("영어 성우", list(VOICES.keys()), index=3)
    
    speed = st.slider("읽기 속도 조절 (%)", -50, 50, 0, step=5)
    pause_time = st.slider("구절 사이 쉬는 시간 (초)", 0.0, 5.0, 1.0, 0.5)
    
    st.write("---")
    bgm_upload = st.file_upload("배경음악(BGM) 업로드 (선택)", type=["mp3", "wav"])

# 메인 입력창
text_input = st.text_area("성경 구절 (한 줄씩 번갈아 입력)", height=300, 
                          placeholder="태초에 하나님이 천지를 창조하시니라.\nIn the beginning God created the heaven and the earth.")

if st.button("고퀄리티 오디오 생성", use_container_width=True):
    if text_input:
        with st.spinner("전문 성우가 녹음 및 믹싱 중입니다..."):
            try:
                # 비동기 실행
                final_audio = asyncio.run(process_project(
                    text_input, VOICES[ko_v], VOICES[en_v], speed, pause_time, bgm_upload
                ))
                
                # 결과 출력
                buffer = io.BytesIO()
                final_audio.export(buffer, format="mp3")
                st.success("✅ 제작이 완료되었습니다!")
                st.audio(buffer.getvalue(), format="audio/mp3")
                st.download_button("최종 MP3 다운로드", buffer.getvalue(), file_name="bible_pro.mp3")
            except Exception as e:
                st.error(f"오류 발생: {e}")
    else:
        st.warning("텍스트를 입력해 주세요.")