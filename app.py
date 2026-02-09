import streamlit as st
import asyncio
import edge_tts
import os
from pydub import AudioSegment
import io
import sys

# --- 3.12 환경 및 오디오 처리 라이브러리 호환성 체크 ---
try:
    import audioop
except ImportError:
    # 파이썬 3.13 이상 대응을 위한 코드 (3.12에서는 통과됨)
    try:
        import audioop_lpm as audioop
        sys.modules['audioop'] = audioop
    except ImportError:
        pass

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
    
    if not audio_data:
        return None
        
    return AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")

async def process_narration(text_data, selected_voice, speed, pause_sec, bgm_file):
    # 줄 단위로 분리 (빈 줄을 제거하지 않음 - 문단 구분용)
    raw_lines = text_data.split('\n')
    combined = AudioSegment.empty()
    
    # 일반 문장 사이 쉬는 시간 (슬라이더 값)
    normal_pause = AudioSegment.silent(duration=int(pause_sec * 1000))
    # 문단 사이 쉬는 시간 (슬라이더 값의 3배로 설정 - 더 길게 쉬고 싶으면 이 숫자를 조절하세요)
    paragraph_pause = AudioSegment.silent(duration=int(pause_sec * 3000))

    for line in raw_lines:
        clean_line = line.strip()
        
        if not clean_line:
            # 빈 줄을 만나면 문단 간격을 추가 (이미 문장이 끝났을 때의 간격이 있으므로 합산됨)
            combined += paragraph_pause
            continue
            
        # 텍스트가 있는 줄 음성 생성
        segment = await generate_audio_segment(clean_line, selected_voice, speed)
        if segment:
            combined += segment + normal_pause

    # BGM 합성 로직
    if bgm_file is not None:
        # 업로드된 파일을 pydub으로 읽기
        bgm = AudioSegment.from_file(bgm_file)
        # B
