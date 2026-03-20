# Core Principles & Rules Engine implementation for the 20-point Dialect list

def is_silence(start_time, last_word_end_time):
    """
    Rule 11: Silence (<SIL>)
    Use when pause > 2 seconds
    """
    return start_time - last_word_end_time > 2.0 and last_word_end_time > 0

def format_silence():
    return "<SIL></SIL>"

def apply_word_rules(original_word):
    """
    Applies word-level taxonomic rules (12, 13, 14, 15) to a single transcribed segment.
    """
    word_lower = original_word.lower()
    
    # Rule 13: Mumbling (<MB>) - Unintelligible speech
    if word_lower in ["[mumbling]", "...", "(mumbling)", "[unintelligible]"]:
        return "<MB></MB>"
        
    # Rule 14: Noise (<NOISE>) - Pure noise with no speech
    if word_lower in ["[noise]", "(noise)", "[background noise]", "[static]"]:
        return "<NOISE></NOISE>"
        
    # Rule 12: Fillers (<FIL>) - Standard Indian/English conversational gap fillers
    fillers = ["ah", "uh", "um", "hmm", "er", "आ", "अ"]
    if word_lower in fillers:
        return f"<FIL>{original_word}</FIL>"
        
    # Rule 14B: Speech WITH Noise
    if "[noise]" in word_lower and word_lower != "[noise]":
        clean_word = original_word.replace("[noise]", "").replace("[Noise]", "").strip()
        return f"<NOISE>{clean_word}</NOISE>"
        
    # Rule 15: Adult Voice Placeholder
    # (If Whisper generated an explicit speaker tag, handle it here. Otherwise, return the verbatim word.)
    if word_lower.startswith("teacher:"):
        clean_word = original_word.replace("Teacher:", "").replace("teacher:", "").strip()
        return f"<ADULT>{clean_word}</ADULT>"
        
    # Rule 1, 2, 4, 5, 9: Return the exact verbatim string (stammers, correct, incorrect readings)
    return original_word

def format_time(seconds_float):
    """
    Rule 6: Timestamping Rules
    Format: HH:MM:SS:MS
    """
    h = int(seconds_float // 3600)
    m = int((seconds_float % 3600) // 60)
    s = int(seconds_float % 60)
    ms = int(round((seconds_float % 1) * 1e6))
    return f"{h}:{m:02d}:{s:02d}.{ms:06d}"
