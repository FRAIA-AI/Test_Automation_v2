import os
import json
import shutil
import subprocess
from pathlib import Path

from elevenlabs.client import ElevenLabs


# ============================================================
# CONFIG
# ============================================================

OUTPUT_ROOT = Path("generated_consultations")

MODEL_ID = "eleven_flash_v2_5"

API_KEY = os.environ.get("ELEVENLABS_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "ELEVENLABS_API_KEY is missing."
    )

client = ElevenLabs(
    api_key=API_KEY
)


# ============================================================
# GET AVAILABLE VOICES
# ============================================================

print("Loading available ElevenLabs voices...")

voice_response = client.voices.get_all()
voices = list(voice_response.voices)

if len(voices) < 4:
    raise RuntimeError(
        "At least 4 available ElevenLabs voices are required."
    )

selected_voices = voices[:4]

ROLE_VOICES = {
    "doctor": selected_voices[0].voice_id,
    "patient": selected_voices[1].voice_id,
    "parent": selected_voices[2].voice_id,
    "child": selected_voices[3].voice_id,
}

ROLE_VOICE_NAMES = {
    "doctor": selected_voices[0].name,
    "patient": selected_voices[1].name,
    "parent": selected_voices[2].name,
    "child": selected_voices[3].name,
}

print("\nSelected voices:")

for role, name in ROLE_VOICE_NAMES.items():
    print(
        f"  {role:8} -> {name}"
    )


# ============================================================
# TEST CASES
# ============================================================

CASES = [

    # --------------------------------------------------------
    # CASE 01 - TWO SPEAKERS
    # --------------------------------------------------------

    {
        "case_id": "case_01",
        "scenario": "doctor_patient",

        # Silence before first speaker
        "intro_pause": 2.0,

        # Silence between turns
        "pause": 0.7,

        "expected_facts": {
            "symptom": "sore throat",
            "fever": True,
            "duration": "three days",
            "medication": "paracetamol",
            "allergies": "none",
        },

        "speaker_facts": {
            "patient": [
                "sore throat",
                "fever",
                "three days",
                "paracetamol",
                "no known allergies",
            ],
            "doctor": [
                "asks about symptoms",
                "asks about medication",
                "asks about allergies",
            ],
        },

        "dialogue": [
            {
                "speaker": "doctor",
                "text":
                    "Hello. What brings you in today?"
            },
            {
                "speaker": "patient",
                "text":
                    "I have had a sore throat and fever "
                    "for about three days."
            },
            {
                "speaker": "doctor",
                "text":
                    "Have you taken any medication?"
            },
            {
                "speaker": "patient",
                "text":
                    "I took paracetamol yesterday evening."
            },
            {
                "speaker": "doctor",
                "text":
                    "Do you have any known allergies?"
            },
            {
                "speaker": "patient",
                "text":
                    "No, I do not have any known allergies."
            },
        ],
    },


    # --------------------------------------------------------
    # CASE 02 - THREE SPEAKERS
    # --------------------------------------------------------

    {
        "case_id": "case_02",
        "scenario": "doctor_patient_parent",

        "intro_pause": 2.5,
        "pause": 0.65,

        "expected_facts": {
            "symptom": "abdominal pain",
            "duration": "two days",
            "fever": True,
            "vomiting": False,
            "temperature": "38.4",
        },

        "speaker_facts": {
            "patient": [
                "abdominal pain",
                "two days",
                "no vomiting",
            ],
            "parent": [
                "fever last night",
                "temperature 38.4",
            ],
            "doctor": [
                "asks about pain",
                "asks about vomiting",
                "asks about fever",
            ],
        },

        "dialogue": [
            {
                "speaker": "doctor",
                "text":
                    "Can you tell me where you are having pain?"
            },
            {
                "speaker": "patient",
                "text":
                    "My stomach has been hurting for two days."
            },
            {
                "speaker": "doctor",
                "text":
                    "Have you vomited?"
            },
            {
                "speaker": "patient",
                "text":
                    "No, I have not vomited."
            },
            {
                "speaker": "parent",
                "text":
                    "He also developed a fever last night."
            },
            {
                "speaker": "doctor",
                "text":
                    "Do you remember the temperature?"
            },
            {
                "speaker": "parent",
                "text":
                    "Yes. It was thirty eight point four degrees."
            },
        ],
    },


    # --------------------------------------------------------
    # CASE 03 - DOCTOR + PATIENT + CHILD
    # --------------------------------------------------------

    {
        "case_id": "case_03",
        "scenario": "doctor_patient_child",

        "intro_pause": 2.0,
        "pause": 0.6,

        "expected_facts": {
            "patient_symptom": "cough",
            "patient_duration": "one week",
            "child_symptom": "runny nose",
            "child_duration": "two days",
        },

        "speaker_facts": {
            "patient": [
                "cough",
                "one week",
            ],
            "child": [
                "runny nose",
                "two days",
            ],
            "doctor": [
                "asks patient about cough",
                "asks child about symptoms",
            ],
        },

        "dialogue": [
            {
                "speaker": "doctor",
                "text":
                    "How long have you had the cough?"
            },
            {
                "speaker": "patient",
                "text":
                    "I have been coughing for around one week."
            },
            {
                "speaker": "doctor",
                "text":
                    "And how are you feeling today?"
            },
            {
                "speaker": "child",
                "text":
                    "My nose keeps running."
            },
            {
                "speaker": "doctor",
                "text":
                    "How long has your nose been like that?"
            },
            {
                "speaker": "child",
                "text":
                    "About two days."
            },
        ],
    },


    # --------------------------------------------------------
    # CASE 04 - FOUR SPEAKERS
    # --------------------------------------------------------

    {
        "case_id": "case_04",
        "scenario":
            "doctor_patient_parent_child",

        "intro_pause": 3.0,
        "pause": 0.55,

        "expected_facts": {
            "patient_symptom": "headache",
            "patient_duration": "four days",
            "parent_observation": "poor sleep",
            "child_observation": "patient tired",
            "medication": "ibuprofen",
        },

        "speaker_facts": {
            "patient": [
                "headache",
                "four days",
                "ibuprofen",
            ],
            "parent": [
                "poor sleep",
            ],
            "child": [
                "patient tired",
            ],
            "doctor": [
                "asks about headache",
                "asks about sleep",
                "asks about medication",
            ],
        },

        "dialogue": [
            {
                "speaker": "doctor",
                "text":
                    "Tell me about the headache."
            },
            {
                "speaker": "patient",
                "text":
                    "I have had a headache for about four days."
            },
            {
                "speaker": "parent",
                "text":
                    "He has also been sleeping very poorly."
            },
            {
                "speaker": "child",
                "text":
                    "Dad has been very tired after work."
            },
            {
                "speaker": "doctor",
                "text":
                    "Have you taken anything for the headache?"
            },
            {
                "speaker": "patient",
                "text":
                    "I took ibuprofen this morning."
            },
            {
                "speaker": "doctor",
                "text":
                    "Did the ibuprofen help?"
            },
            {
                "speaker": "patient",
                "text":
                    "Only a little."
            },
        ],
    },


    # --------------------------------------------------------
    # CASE 05 - FAST TURN TAKING
    # --------------------------------------------------------

    {
        "case_id": "case_05",
        "scenario":
            "rapid_three_speaker_conversation",

        "intro_pause": 2.0,

        # Very short gaps between speakers
        "pause": 0.15,

        "expected_facts": {
            "symptom": "dizziness",
            "trigger": "standing up",
            "duration": "five days",
            "blood_pressure": "low",
            "fall": False,
        },

        "speaker_facts": {
            "patient": [
                "dizziness",
                "standing up",
                "five days",
                "no fall",
            ],
            "parent": [
                "blood pressure low",
            ],
            "doctor": [
                "asks about dizziness",
                "asks about falling",
            ],
        },

        "dialogue": [
            {
                "speaker": "doctor",
                "text":
                    "When do you normally feel dizzy?"
            },
            {
                "speaker": "patient",
                "text":
                    "Mostly when I stand up."
            },
            {
                "speaker": "parent",
                "text":
                    "His blood pressure has also been low."
            },
            {
                "speaker": "doctor",
                "text":
                    "How long has this been happening?"
            },
            {
                "speaker": "patient",
                "text":
                    "About five days."
            },
            {
                "speaker": "doctor",
                "text":
                    "Have you fallen or lost consciousness?"
            },
            {
                "speaker": "patient",
                "text":
                    "No. I have not fallen."
            },
            {
                "speaker": "parent",
                "text":
                    "But yesterday he nearly lost his balance."
            },
        ],
    },
]


# ============================================================
# AUDIO FUNCTIONS
# ============================================================

def generate_speech(
    text,
    voice_id,
    output_file,
):
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=MODEL_ID,
        text=text,
        output_format="mp3_44100_128",
    )

    with open(
        output_file,
        "wb",
    ) as file:
        for chunk in audio:
            file.write(chunk)


def generate_silence(
    output_file,
    duration,
):
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-t", str(duration),
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            str(output_file),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def concatenate(
    files,
    case_folder,
):
    concat_file = (
        case_folder
        / "concat.txt"
    )

    with open(
        concat_file,
        "w",
        encoding="utf-8",
    ) as file:

        for audio_file in files:

            file.write(
                "file "
                f"'{audio_file.resolve().as_posix()}'"
                "\n"
            )

    combined_mp3 = (
        case_folder
        / "combined.mp3"
    )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),

            # Re-encode instead of stream-copying
            "-c:a", "libmp3lame",
            "-ar", "44100",
            "-ac", "1",
            "-b:a", "128k",

            str(combined_mp3),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return (
        combined_mp3,
        concat_file,
    )


def create_webm(
    input_file,
    output_file,
):
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i", str(input_file),

            "-vn",

            "-c:a", "libopus",

            "-ar", "48000",

            "-ac", "1",

            "-b:a", "96k",

            str(output_file),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ============================================================
# GENERATE ONE CASE
# ============================================================

def generate_case(case):

    case_id = case["case_id"]

    print()
    print("=" * 60)
    print(
        f"Generating {case_id}"
    )
    print(
        f"Scenario: {case['scenario']}"
    )
    print("=" * 60)

    case_folder = (
        OUTPUT_ROOT
        / case_id
    )

    # Recreate case folder cleanly
    if case_folder.exists():
        shutil.rmtree(
            case_folder
        )

    case_folder.mkdir(
        parents=True
    )

    audio_parts = []
    temporary_files = []


    # --------------------------------------------------------
    # INTRO SILENCE
    # --------------------------------------------------------

    intro_duration = case.get(
        "intro_pause",
        2.0,
    )

    intro_file = (
        case_folder
        / "intro_pause.mp3"
    )

    print(
        f"  Intro silence: "
        f"{intro_duration} seconds"
    )

    generate_silence(
        intro_file,
        duration=intro_duration,
    )

    audio_parts.append(
        intro_file
    )

    temporary_files.append(
        intro_file
    )


    # --------------------------------------------------------
    # DIALOGUE
    # --------------------------------------------------------

    dialogue = case["dialogue"]

    for index, turn in enumerate(
        dialogue,
        start=1,
    ):

        speaker = turn["speaker"]
        text = turn["text"]

        voice_id = (
            ROLE_VOICES[speaker]
        )

        speech_file = (
            case_folder
            / f"{index:02d}_{speaker}.mp3"
        )

        print(
            f"  {index:02d} "
            f"{speaker}: "
            f"{text}"
        )

        generate_speech(
            text,
            voice_id,
            speech_file,
        )

        audio_parts.append(
            speech_file
        )

        temporary_files.append(
            speech_file
        )


        # ----------------------------------------------------
        # PAUSE BETWEEN SPEAKERS
        # ----------------------------------------------------

        if index < len(dialogue):

            pause_file = (
                case_folder
                / f"{index:02d}_pause.mp3"
            )

            generate_silence(
                pause_file,
                case["pause"],
            )

            audio_parts.append(
                pause_file
            )

            temporary_files.append(
                pause_file
            )


    # --------------------------------------------------------
    # COMBINE AUDIO
    # --------------------------------------------------------

    print(
        "  Combining audio..."
    )

    combined_mp3, concat_file = (
        concatenate(
            audio_parts,
            case_folder,
        )
    )


    # --------------------------------------------------------
    # CREATE FINAL WEBM
    # --------------------------------------------------------

    final_webm = (
        case_folder
        / "consultation.webm"
    )

    print(
        "  Creating WebM..."
    )

    create_webm(
        combined_mp3,
        final_webm,
    )


    # --------------------------------------------------------
    # CREATE ORACLE
    # --------------------------------------------------------

    speakers_used = sorted(
        set(
            turn["speaker"]
            for turn
            in dialogue
        )
    )

    oracle = {

        "case_id":
            case_id,

        "scenario":
            case["scenario"],

        "intro_pause_seconds":
            intro_duration,

        "inter_turn_pause_seconds":
            case["pause"],

        "speaker_count":
            len(speakers_used),

        "speakers":
            {
                role: {
                    "voice_id":
                        ROLE_VOICES[role],

                    "voice_name":
                        ROLE_VOICE_NAMES[role],
                }

                for role
                in speakers_used
            },

        "expected_facts":
            case[
                "expected_facts"
            ],

        "speaker_facts":
            case[
                "speaker_facts"
            ],

        "dialogue":
            dialogue,
    }


    oracle_file = (
        case_folder
        / "oracle.json"
    )

    with open(
        oracle_file,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            oracle,
            file,
            indent=2,
            ensure_ascii=False,
        )


    # --------------------------------------------------------
    # CLEAN TEMPORARY FILES
    # --------------------------------------------------------

    print(
        "  Cleaning temporary files..."
    )

    for file in temporary_files:

        if file.exists():
            file.unlink()


    if combined_mp3.exists():
        combined_mp3.unlink()

    if concat_file.exists():
        concat_file.unlink()


    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    print(
        f"  DONE -> {final_webm}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_ROOT.mkdir(
        exist_ok=True
    )

    print()
    print(
        "Diarization batch generation"
    )
    print(
        f"Cases: {len(CASES)}"
    )

    for case in CASES:
        generate_case(case)

    print()
    print("=" * 60)
    print("ALL CASES GENERATED")
    print("=" * 60)

    print(
        f"Folder: {OUTPUT_ROOT.resolve()}"
    )


if __name__ == "__main__":
    main()