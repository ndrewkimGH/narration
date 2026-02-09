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
    # rate 설정 (예: +0%, -10% 등)
    rate_str = f"{rate:+d}%"
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    
    return AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")

async def process_narration(text_data, selected_voice, speed, pause_sec, bgm_file):
    # 빈 줄을 제외하고 문장 단위로 나눔
    lines = [line.strip() for line in text_data.split('\n') if line.strip()]
    combined = AudioSegment.empty()
    # 문장 사이 쉬는 시간
    pause = AudioSegment.silent(duration=int(pause_sec * 1000))

    for line in lines:
        # 선택된 단 한 명의 성우가 모든 문장을 읽음
        segment = await generate_audio_segment(line, selected_voice, speed)
        combined += segment + pause

    # BGM 합성 로직
    if bgm_file is not None:
        bgm = AudioSegment.from_file(bgm_file)
        bgm = bgm - 25 # 배경음악 볼륨 조정
        if len(bgm) < len(combined):
            bgm = bgm * (len(combined) // len(bgm) + 1)
        bgm = bgm[:len(combined)]
        combined = combined.overlay(bgm)

    return combined

# --- UI 레이아웃 ---
st.set_page_config(page_title="나만의 오디오북 제작기", layout="wide")
st.title("🎙️ 통합 나레이션 제작 스튜디오")

with st.sidebar:
    st.header("👤 성우 및 효과 설정")
    # 이제 성우를 한 명만 선택합니다.
    chosen_voice_name = st.selectbox("낭독할 성우 선택", list(VOICES.keys()))
    chosen_voice_code = VOICES[chosen_voice_name]
    
    speed = st.slider("읽기 속도 조절 (%)", -50, 50, 0, step=5)
    pause_time = st.slider("문장 사이 간격 (초)", 0.0, 5.0, 1.0, 0.5)
    
    st.write("---")
    bgm_upload = st.file_uploader("배경음악(BGM) 업로드", type=["mp3", "wav"])

# 메인 입력창
text_input = st.text_area("낭독할 스크립트 입력 (한글/영어 자유롭게)", height=400, 
                          placeholder="여기에 낭독할 내용을 입력하세요. 한글과 영어가 섞여 있어도 선택한 성우가 모두 읽습니다.")

if st.button("오디오 제작 시작", use_container_width=True):
    if text_input:
        with st.spinner(f"{chosen_voice_name} 성우가 낭독 중입니다..."):
            try:
                # 3.12 환경을 위한 이벤트 루프 설정
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                final_audio = loop.run_until_complete(process_narration(
                    text_input, chosen_voice_code, speed, pause_time, bgm_upload
                ))
                
                # 결과 출력
                buffer = io.BytesIO()
                final_audio.export(buffer, format="mp3")
                st.success("✅ 제작 완료!")
                st.audio(buffer.getvalue(), format="audio/mp3")
                st.download_button("최종 MP3 다운로드", buffer.getvalue(), file_name="narration_output.mp3")
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
    else:
        st.warning("내용을 입력해 주세요.")
