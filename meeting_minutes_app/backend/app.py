"""
Meeting Minutes Web Application - Backend API
基于 Microsoft VibeVoice ASR 模型的会议纪要生成服务
"""

import os
import json
import time
import tempfile
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

import torch
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import uvicorn

# Import VibeVoice ASR components
from vibevoice.modular.modeling_vibevoice_asr import VibeVoiceASRForConditionalGeneration
from vibevoice.processor.vibevoice_asr_processor import VibeVoiceASRProcessor
from vibevoice.processor.audio_utils import load_audio_use_ffmpeg, COMMON_AUDIO_EXTS

# Try to import optional dependencies
try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False
    print("⚠️ Warning: pydub not available, MP3 conversion may not work")

# Configuration
MODEL_PATH = os.environ.get("MODEL_PATH", "microsoft/VibeVoice-ASR")
DEVICE = os.environ.get("MODEL_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
DTYPE = torch.bfloat16 if DEVICE == "cuda" else torch.float32
MAX_AUDIO_DURATION = 60 * 60  # 60 minutes in seconds
TEMP_DIR = Path(tempfile.gettempdir()) / "meeting_minutes"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Meeting Minutes API",
    description="AI-powered meeting transcription and summarization using VibeVoice ASR",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TranscriptionSegment(BaseModel):
    speaker_id: str
    start_time: float
    end_time: float
    text: str


class TranscriptionResult(BaseModel):
    status: str
    audio_duration: float
    segments: List[TranscriptionSegment]
    full_text: str
    processing_time: float
    model_info: Dict[str, Any]
    error: Optional[str] = None


class MeetingSummary(BaseModel):
    key_points: List[str]
    decisions: List[str]
    action_items: List[Dict[str, str]]
    speaker_stats: Dict[str, Dict[str, Any]]


# Global model instance
asr_model = None
asr_processor = None


def load_model():
    """Load the VibeVoice ASR model"""
    global asr_model, asr_processor
    
    print(f"🔄 Loading VibeVoice ASR model from {MODEL_PATH}...")
    print(f"📍 Device: {DEVICE}, Dtype: {DTYPE}")
    
    try:
        # Load processor
        asr_processor = VibeVoiceASRProcessor.from_pretrained(MODEL_PATH)
        
        # Determine attention implementation
        attn_impl = "flash_attention_2" if DEVICE == "cuda" else "sdpa"
        print(f"🔧 Using attention implementation: {attn_impl}")
        
        # Load model
        asr_model = VibeVoiceASRForConditionalGeneration.from_pretrained(
            MODEL_PATH,
            dtype=DTYPE,
            device_map=DEVICE if DEVICE != "cpu" else None,
            attn_implementation=attn_impl,
            trust_remote_code=True
        )
        
        if DEVICE == "cpu":
            asr_model = asr_model.to(DEVICE)
        
        asr_model.eval()
        
        total_params = sum(p.numel() for p in asr_model.parameters())
        print(f"✅ Model loaded successfully!")
        print(f"📊 Total parameters: {total_params:,} ({total_params/1e9:.2f}B)")
        
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        traceback.print_exc()
        raise


@app.on_event("startup")
async def startup_event():
    """Initialize model on startup"""
    load_model()
    print("🚀 Meeting Minutes API is ready!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global asr_model
    if asr_model is not None:
        del asr_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print("👋 Model cleaned up")


def validate_audio_file(file_path: Path) -> dict:
    """Validate audio file format and duration"""
    try:
        # Load audio to check duration
        audio_data, sample_rate = load_audio_use_ffmpeg(str(file_path), resample=False)
        duration = len(audio_data) / sample_rate
        
        if duration > MAX_AUDIO_DURATION:
            return {
                "valid": False,
                "error": f"Audio duration ({duration:.1f}s) exceeds maximum allowed ({MAX_AUDIO_DURATION}s)"
            }
        
        return {
            "valid": True,
            "duration": duration,
            "sample_rate": sample_rate,
            "samples": len(audio_data)
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Failed to load audio file: {str(e)}"
        }


def transcribe_audio(
    audio_path: str,
    context_info: Optional[str] = None,
    max_new_tokens: int = 2048
) -> dict:
    """Transcribe audio using VibeVoice ASR"""
    global asr_model, asr_processor
    
    if asr_model is None or asr_processor is None:
        raise RuntimeError("Model not loaded")
    
    start_time = time.time()
    
    # Process audio
    inputs = asr_processor(
        audio=audio_path,
        sampling_rate=None,
        return_tensors="pt",
        add_generation_prompt=True,
        context_info=context_info
    )
    
    # Move to device
    device = next(asr_model.parameters()).device
    inputs = {k: v.to(device) if isinstance(v, torch.Tensor) else v 
              for k, v in inputs.items()}
    
    # Calculate input statistics
    input_ids = inputs['input_ids'][0]
    total_input_tokens = input_ids.shape[0]
    
    # Generate
    with torch.no_grad():
        output_ids = asr_model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.0,
            do_sample=False,
            num_beams=1,
            pad_token_id=asr_processor.pad_id,
            eos_token_id=asr_processor.tokenizer.eos_token_id,
        )
    
    generation_time = time.time() - start_time
    
    # Decode output
    generated_ids = output_ids[0, inputs['input_ids'].shape[1]:]
    generated_text = asr_processor.decode(generated_ids, skip_special_tokens=True)
    
    # Parse structured output
    try:
        transcription_segments = asr_processor.post_process_transcription(generated_text)
    except Exception as e:
        print(f"⚠️ Warning: Failed to parse structured output: {e}")
        transcription_segments = []
    
    return {
        "raw_text": generated_text,
        "segments": transcription_segments,
        "generation_time": generation_time,
        "input_tokens": total_input_tokens,
        "output_tokens": len(generated_ids),
    }


def generate_summary(segments: List[dict]) -> dict:
    """Generate meeting summary from transcription segments"""
    # Calculate speaker statistics
    speaker_stats = {}
    for seg in segments:
        speaker_id = seg.get('speaker_id', 'Unknown')
        duration = seg.get('end_time', 0) - seg.get('start_time', 0)
        text = seg.get('text', '')
        
        if speaker_id not in speaker_stats:
            speaker_stats[speaker_id] = {
                "total_duration": 0,
                "segment_count": 0,
                "word_count": 0
            }
        
        speaker_stats[speaker_id]["total_duration"] += duration
        speaker_stats[speaker_id]["segment_count"] += 1
        speaker_stats[speaker_id]["word_count"] += len(text.split())
    
    # Simple heuristic-based summary (can be enhanced with LLM)
    all_text = " ".join([seg.get('text', '') for seg in segments])
    
    # Extract key sentences (simple approach)
    sentences = all_text.split('.')
    key_points = [s.strip() for s in sentences[:5] if len(s.strip()) > 20]
    
    # Identify potential action items (sentences with action verbs)
    action_verbs = ['will', 'should', 'must', 'need to', 'have to', 'action', 'task']
    action_items = []
    for seg in segments:
        text = seg.get('text', '').lower()
        if any(verb in text for verb in action_verbs):
            action_items.append({
                "description": seg.get('text', ''),
                "speaker": seg.get('speaker_id', 'Unknown')
            })
    
    return {
        "key_points": key_points[:5],
        "decisions": [],  # Can be enhanced with NLP
        "action_items": action_items[:5],
        "speaker_stats": speaker_stats
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Meeting Minutes API",
        "version": "1.0.0",
        "model": MODEL_PATH,
        "device": DEVICE,
        "status": "ready" if asr_model is not None else "loading"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": asr_model is not None,
        "device": DEVICE,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/transcribe", response_model=TranscriptionResult)
async def transcribe_endpoint(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    context_info: Optional[str] = Form(None, description="Optional context/hotwords to improve accuracy"),
    max_new_tokens: int = Form(2048, description="Maximum tokens to generate")
):
    """
    Transcribe an audio file to text with speaker diarization and timestamps
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    supported_exts = COMMON_AUDIO_EXTS + ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.webm')
    
    if file_ext not in supported_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {file_ext}. Supported: {supported_exts}"
        )
    
    # Save uploaded file
    temp_file = TEMP_DIR / f"{int(time.time())}_{file.filename}"
    try:
        content = await file.read()
        temp_file.write_bytes(content)
        
        # Validate audio
        validation = validate_audio_file(temp_file)
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail=validation["error"])
        
        audio_duration = validation["duration"]
        
        # Transcribe
        result = transcribe_audio(
            str(temp_file),
            context_info=context_info,
            max_new_tokens=max_new_tokens
        )
        
        # Format segments
        formatted_segments = [
            TranscriptionSegment(
                speaker_id=seg.get('speaker_id', 'Unknown'),
                start_time=seg.get('start_time', 0),
                end_time=seg.get('end_time', 0),
                text=seg.get('text', '')
            )
            for seg in result["segments"]
        ]
        
        # Full text
        full_text = "\n".join([
            f"[{seg.start_time:.2f}s - {seg.end_time:.2f}s] {seg.speaker_id}: {seg.text}"
            for seg in formatted_segments
        ])
        
        return TranscriptionResult(
            status="success",
            audio_duration=audio_duration,
            segments=formatted_segments,
            full_text=full_text,
            processing_time=result["generation_time"],
            model_info={
                "model_path": MODEL_PATH,
                "device": DEVICE,
                "input_tokens": result["input_tokens"],
                "output_tokens": result["output_tokens"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        # Cleanup temp file
        if temp_file.exists():
            temp_file.unlink()


@app.post("/transcribe-and-summarize")
async def transcribe_and_summarize(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    context_info: Optional[str] = Form(None, description="Optional context/hotwords")
):
    """
    Transcribe audio and generate a meeting summary
    """
    # Reuse transcribe logic
    file_ext = Path(file.filename).suffix.lower()
    supported_exts = COMMON_AUDIO_EXTS + ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.webm')
    
    if file_ext not in supported_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {file_ext}"
        )
    
    temp_file = TEMP_DIR / f"{int(time.time())}_{file.filename}"
    try:
        content = await file.read()
        temp_file.write_bytes(content)
        
        validation = validate_audio_file(temp_file)
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail=validation["error"])
        
        # Transcribe
        result = transcribe_audio(str(temp_file), context_info=context_info)
        
        # Generate summary
        summary = generate_summary(result["segments"])
        
        return {
            "status": "success",
            "audio_duration": validation["duration"],
            "transcription": {
                "segments": result["segments"],
                "full_text": result["raw_text"]
            },
            "summary": summary,
            "processing_time": result["generation_time"]
        }
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        if temp_file.exists():
            temp_file.unlink()


@app.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported audio formats"""
    return {
        "formats": COMMON_AUDIO_EXTS + ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.webm'),
        "max_duration_seconds": MAX_AUDIO_DURATION,
        "max_duration_formatted": f"{MAX_AUDIO_DURATION // 60} minutes"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
