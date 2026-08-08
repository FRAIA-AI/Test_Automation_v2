"""AI evaluation for People's Clinic diarization + generated clinical notes.

This script does NOT run browser consultations.

It evaluates results already collected by:

    tests/diarization/test_diarization_batch.py

For each case it reads:

    generated_consultations/case_XX/oracle.json

and:

    results/diarization/case_XX/diarized-transcription.txt
    results/diarization/case_XX/generated-note.txt

It evaluates TWO separate product layers:

1. DIARIZATION
   - transcription content retention
   - doctor attribution
   - patient-side attribution
   - overall doctor-vs-patient-side routing quality
   - unsupported transcription content

2. GENERATED CLINICAL NOTE
   - clinical fact retention
   - clinical fidelity
   - unsupported / hallucinated clinical facts

IMPORTANT PRODUCT BEHAVIOR:

People's Clinic currently exposes two diarization buckets:

    Læge    = doctor / clinician
    Patient = everyone on the patient side

Therefore:
    doctor -> Læge
    patient -> Patient
    parent -> Patient
    child -> Patient
    spouse -> Patient
    caregiver -> Patient

Parent and child are NOT expected to receive their own output labels.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from statistics import mean
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field


# ============================================================
# CONFIG
# ============================================================

MODEL = os.environ.get(
    "OPENAI_EVALUATION_MODEL",
    "gpt-5.6-luna",
)

CASES_ROOT = Path(
    os.environ.get(
        "DIARIZATION_CASES_DIR",
        "test_data/diarization",
    )
)

RESULTS_ROOT = Path(
    "results/diarization"
)

EVALUATION_ROOT = (
    RESULTS_ROOT
    / "evaluation"
)


# ============================================================
# CASE SELECTION
# ============================================================

def discover_case_ids(cases_root: Path) -> list[str]:
    """Use every versioned fixture, or every case in a local private corpus."""

    return sorted(
        (
            path.name
            for path in cases_root.glob("case_*")
            if path.is_dir()
        ),
        key=lambda case_id: int(case_id.removeprefix("case_")),
    )


CASE_IDS = discover_case_ids(CASES_ROOT)


# ============================================================
# OPENAI CLIENT
# ============================================================

if not os.environ.get(
    "OPENAI_API_KEY"
):
    raise RuntimeError(
        "OPENAI_API_KEY is missing.\n"
        "WSL/Linux example:\n"
        'export OPENAI_API_KEY="sk-..."\n'
        "\n"
        "PowerShell example:\n"
        '$env:OPENAI_API_KEY="sk-..."'
    )

client = OpenAI()


# ============================================================
# STRUCTURED RESULT MODELS
# ============================================================

class AttributionError(BaseModel):
    """One source utterance placed in the wrong product bucket."""

    expected_bucket: Literal[
        "doctor",
        "patient_side",
    ]

    actual_bucket: Literal[
        "doctor",
        "patient_side",
        "missing",
        "unclear",
    ]

    source_role: str

    source_text: str

    observed_text: str | None = None

    explanation: str


class MissingContent(BaseModel):
    """Ground-truth content missing from transcription."""

    source_role: str

    source_text: str

    explanation: str


class HallucinatedContent(BaseModel):
    """Content appearing in transcription without source support."""

    observed_text: str

    assigned_bucket: Literal[
        "doctor",
        "patient_side",
        "unclear",
    ]

    explanation: str


class CaseEvaluation(BaseModel):
    """Structured AI evaluation for one consultation case."""

    # --------------------------------------------------------
    # IDENTIFICATION
    # --------------------------------------------------------

    case_id: str

    scenario: str

    # --------------------------------------------------------
    # TRANSCRIPTION CONTENT
    # --------------------------------------------------------

    content_retention_score: int = Field(
        ge=0,
        le=100,
        description=(
            "How completely semantic content from the "
            "ground-truth consultation survives in the "
            "actual diarized transcription."
        ),
    )

    # --------------------------------------------------------
    # DIARIZATION / ATTRIBUTION
    # --------------------------------------------------------

    doctor_attribution_score: int = Field(
        ge=0,
        le=100,
        description=(
            "How accurately doctor utterances are assigned "
            "to the Læge/doctor bucket."
        ),
    )

    patient_side_attribution_score: int = Field(
        ge=0,
        le=100,
        description=(
            "How accurately patient, parent, child, spouse, "
            "caregiver, and other non-doctor utterances are "
            "assigned to the Patient/patient-side bucket."
        ),
    )

    overall_attribution_score: int = Field(
        ge=0,
        le=100,
        description=(
            "Overall doctor-versus-patient-side speaker "
            "attribution quality."
        ),
    )

    hallucination_score: int = Field(
        ge=0,
        le=100,
        description=(
            "100 means the transcription contains no "
            "material unsupported/invented content."
        ),
    )

    # AI may return these, but Python will overwrite them
    # deterministically after parsing.

    overall_score: int = Field(
        ge=0,
        le=100,
    )

    verdict: Literal[
        "excellent",
        "good",
        "degraded",
        "poor",
    ]

    # --------------------------------------------------------
    # TURN COUNTS
    # --------------------------------------------------------

    expected_turn_count: int

    evaluated_turn_count: int

    correctly_attributed_turns: int

    misattributed_turns: int

    missing_turns: int

    # --------------------------------------------------------
    # DIARIZATION FINDINGS
    # --------------------------------------------------------

    attribution_errors: list[
        AttributionError
    ]

    missing_content: list[
        MissingContent
    ]

    hallucinated_content: list[
        HallucinatedContent
    ]

    # --------------------------------------------------------
    # GENERATED CLINICAL NOTE
    # --------------------------------------------------------

    clinical_fact_retention_score: int = Field(
        ge=0,
        le=100,
        description=(
            "How completely clinically meaningful facts "
            "from the original consultation are preserved "
            "in the generated clinical note."
        ),
    )

    clinical_note_fidelity_score: int = Field(
        ge=0,
        le=100,
        description=(
            "How accurately the generated clinical note "
            "represents the original consultation."
        ),
    )

    clinical_note_hallucination_score: int = Field(
        ge=0,
        le=100,
        description=(
            "100 means the generated clinical note contains "
            "no unsupported clinically meaningful facts."
        ),
    )

    clinically_missing_facts: list[str]

    clinically_invented_facts: list[str]

    clinical_note_summary: str

    # --------------------------------------------------------
    # OVERALL INTERPRETATION
    # --------------------------------------------------------

    summary: str


# ============================================================
# DETERMINISTIC SCORING
# ============================================================

def calculate_diarization_overall(
    *,
    attribution: int,
    content: int,
    integrity: int,
) -> int:
    """
    Fixed weighted diarization score.

    55% attribution
    35% content retention
    10% transcription integrity
    """

    score = (
        attribution * 0.55
        + content * 0.35
        + integrity * 0.10
    )

    return round(
        score
    )


def calculate_verdict(
    score: int,
) -> str:
    """
    Fixed verdict thresholds.

    excellent = 95-100
    good      = 85-94
    degraded  = 65-84
    poor      = below 65
    """

    if score >= 95:
        return "excellent"

    if score >= 85:
        return "good"

    if score >= 65:
        return "degraded"

    return "poor"


# ============================================================
# FILE HELPERS
# ============================================================

def load_oracle(
    case_id: str,
) -> dict:
    """Load the known original consultation oracle."""

    oracle_file = (
        CASES_ROOT
        / case_id
        / "oracle.json"
    )

    if not oracle_file.exists():
        raise FileNotFoundError(
            f"Missing oracle: "
            f"{oracle_file}"
        )

    return json.loads(
        oracle_file.read_text(
            encoding="utf-8"
        )
    )


def load_diarized_transcription(
    case_id: str,
) -> str:
    """Load the platform's diarized transcription."""

    transcription_file = (
        RESULTS_ROOT
        / case_id
        / "diarized-transcription.txt"
    )

    if not transcription_file.exists():
        raise FileNotFoundError(
            "Missing diarized transcription: "
            f"{transcription_file}"
        )

    transcription = (
        transcription_file
        .read_text(
            encoding="utf-8"
        )
        .strip()
    )

    if (
        not transcription
        or transcription == "[EMPTY]"
    ):
        raise RuntimeError(
            f"{case_id}: diarized transcription "
            "is empty."
        )

    return transcription


def load_generated_note(
    case_id: str,
) -> str:
    """Load the clinical note generated on the Edit Note page."""

    note_file = (
        RESULTS_ROOT
        / case_id
        / "generated-note.txt"
    )

    if not note_file.exists():
        raise FileNotFoundError(
            f"Missing generated note: "
            f"{note_file}"
        )

    note = (
        note_file
        .read_text(
            encoding="utf-8"
        )
        .strip()
    )

    if (
        not note
        or note == "[EMPTY]"
    ):
        raise RuntimeError(
            f"{case_id}: generated clinical "
            "note is empty."
        )

    return note


# ============================================================
# NORMALIZE ORACLE TO PRODUCT'S TWO SPEAKER BUCKETS
# ============================================================

def create_expected_dialogue(
    oracle: dict,
) -> list[dict]:
    """
    Convert source roles into the two buckets exposed by
    People's Clinic.

    doctor:
        doctor

    patient/parent/child/etc:
        patient_side
    """

    expected = []

    for index, turn in enumerate(
        oracle.get(
            "dialogue",
            [],
        ),
        start=1,
    ):
        source_role = (
            str(
                turn.get(
                    "speaker",
                    "",
                )
            )
            .strip()
            .lower()
        )

        if source_role == "doctor":
            expected_bucket = "doctor"

        else:
            expected_bucket = (
                "patient_side"
            )

        expected.append(
            {
                "turn_number":
                    index,

                "source_role":
                    source_role,

                "expected_bucket":
                    expected_bucket,

                "text":
                    str(
                        turn.get(
                            "text",
                            "",
                        )
                    ),
            }
        )

    return expected


# ============================================================
# AI EVALUATION PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are evaluating a clinical consultation transcription and
note-generation system.

This is a software quality evaluation task.

You are given:

1. The ORIGINAL ground-truth consultation dialogue.
2. Expected clinically meaningful facts from the oracle.
3. The platform's actual diarized transcription.
4. The generated clinical note from the Edit Note page.

You must evaluate TWO distinct product layers:

A. DIARIZATION / TRANSCRIPTION
B. GENERATED CLINICAL NOTE

Never merge those two evaluations into one judgment.


============================================================
A. PRODUCT SPEAKER MODEL
============================================================

The original ground-truth consultation may contain roles such
as:

- doctor
- patient
- parent
- child
- spouse
- caregiver
- another family member

However, the product being tested exposes ONLY TWO output
speaker buckets:

1. "Læge" = doctor / clinician
2. "Patient" = everyone on the patient side

Therefore the expected mapping is:

doctor    -> doctor / Læge
patient   -> patient_side / Patient
parent    -> patient_side / Patient
child     -> patient_side / Patient
spouse    -> patient_side / Patient
caregiver -> patient_side / Patient

DO NOT penalize the product because parent, child, spouse,
or caregiver labels are not preserved separately.

For this product, those speakers are intentionally expected
to appear under Patient.


============================================================
B. DIARIZATION EVALUATION
============================================================

Evaluate whether content from each source turn survived and
whether it was placed into the correct TWO-BUCKET speaker
category.

DO penalize:

- doctor speech placed under Patient
- patient-side speech placed under Læge
- omitted meaningful source content
- materially altered meaning
- unsupported/invented transcription content

DO NOT penalize:

- punctuation differences
- capitalization
- contractions
- harmless wording differences
- harmless ASR paraphrases
- Danish "Læge" versus English "Doctor"
- splitting one source turn into multiple adjacent segments
- merging adjacent non-doctor source turns under Patient
- merging parent/child/patient content together under Patient

The product does not need to distinguish individual
patient-side speakers.


CONTENT RETENTION SCORE

100:
Essentially all meaningful spoken content survived.

90-99:
Tiny omissions or harmless degradation.

75-89:
Noticeable information loss.

50-74:
Major information loss.

0-49:
Severe transcription failure.


ATTRIBUTION SCORES

100:
Essentially all content routed to the correct doctor or
patient-side bucket.

90-99:
Very small routing error.

75-89:
Several meaningful attribution errors.

50-74:
Substantial doctor/patient-side confusion.

0-49:
Severe diarization failure.


TRANSCRIPTION HALLUCINATION SCORE

100:
No meaningful unsupported additions.

Reduce the score only when the transcription materially adds
content that was not in the source consultation.


IMPORTANT:

You may populate overall_score and verdict because they are
required by the schema, but the application will IGNORE them
and calculate them deterministically in Python.


============================================================
C. GENERATED CLINICAL NOTE EVALUATION
============================================================

Evaluate the generated clinical note against the ORIGINAL
ground-truth consultation.

Do NOT evaluate the note only against the transcription.

This distinction is extremely important:

A diarization error may occur while the final note still
contains the correct clinically meaningful information.

Likewise, the transcription may be accurate while the note
can omit or invent medical information.


------------------------------------------------------------
1. CLINICAL FACT RETENTION
------------------------------------------------------------

Determine whether clinically meaningful facts from the
ORIGINAL consultation were retained appropriately.

Relevant examples include:

- main complaint
- symptom
- symptom location
- duration
- severity
- onset
- triggers
- associated symptoms
- important negative findings reported by speakers
- medications
- allergies
- measured temperature
- blood pressure
- family observations
- relevant history
- response to medication

Doctor questions and conversational filler generally do not
need to appear in the clinical note.

Do not require verbatim copying.

Professional medical summarization is allowed.


Clinical fact retention:

100:
Essentially all appropriate clinically meaningful facts
preserved.

90-99:
Minor clinically unimportant omission.

75-89:
Noticeable clinically relevant omissions.

50-74:
Major information loss.

0-49:
Severe note-generation failure.


------------------------------------------------------------
2. CLINICAL NOTE FIDELITY
------------------------------------------------------------

Judge whether facts included in the note accurately represent
the original consultation.

Allow professional rewording.

Do NOT penalize appropriate concise summarization.

DO penalize:

- changing positive to negative
- changing negative to positive
- wrong duration
- wrong medication
- wrong symptom
- wrong body side
- wrong measurement
- incorrect event sequence
- unsupported certainty
- material distortion
- presenting something as observed when it was never observed


Clinical note fidelity:

100:
Essentially completely faithful.

90-99:
Tiny inaccuracies without meaningful consequence.

75-89:
Meaningful inaccuracies.

50-74:
Substantial distortion.

0-49:
Severely unreliable.


------------------------------------------------------------
3. CLINICAL NOTE HALLUCINATION INTEGRITY
------------------------------------------------------------

This score is particularly important.

100 means the generated note introduces NO clinically
meaningful unsupported facts.

The ORIGINAL consultation dialogue and oracle are the source
of truth.

Do not assume that an examination occurred merely because
the generated note contains an Objective section.

Penalize unsupported clinical statements such as invented:

- physical examination results
- neurological examination results
- laboratory values
- vital signs
- diagnoses stated as established facts
- medications
- treatment recommendations
- imaging results
- history
- allergies
- symptoms
- measurements

Example:

If the source consultation only contains:

"I will examine your neck."

but the generated note says:

"Strength 5/5 bilaterally.
Sensation intact.
No meningism.
No palpable tenderness."

those findings are UNSUPPORTED unless they were actually
present in the original consultation.

Do not excuse invented Objective findings just because they
sound medically plausible.

However, reasonable summarizing diagnostic language may be
acceptable when clearly presented as an assessment or likely
interpretation AND supported by the source facts.

Be stricter with claims presented as measured, observed, or
examined findings.


Clinical note hallucination integrity:

100:
No unsupported clinically meaningful content.

90-99:
Very minor unsupported claim.

75-89:
Several or meaningful unsupported claims.

50-74:
Substantial invented clinical information.

0-49:
Severely unsafe/unreliable fabrication.


============================================================
D. TURN COUNTING
============================================================

The ground-truth dialogue contains source turns.

The platform may split or merge text.

Therefore:

- expected_turn_count must equal the number of source turns.
- evaluated_turn_count should reflect how many source turns
  you could meaningfully evaluate against the transcription.
- correctly_attributed_turns counts source turns whose
  semantic content appears in the correct product bucket.
- misattributed_turns counts source turns whose content is
  materially routed to the wrong bucket.
- missing_turns counts source turns whose meaningful content
  is absent.

If one source turn gets split into multiple transcript lines,
count it as one source turn for these metrics.

If multiple source turns are merged, evaluate each source
turn separately.


============================================================
E. REQUIRED OUTPUT BEHAVIOR
============================================================

Be strict but fair.

Use semantic comparison, not exact string comparison.

Do not invent errors merely because wording differs.

List every clear speaker-attribution error.

List meaningful missing source content.

List meaningful unsupported transcription content.

For the generated note:

- list meaningful missing clinical facts
- list meaningful unsupported/invented clinical facts

The clinical note evaluation must always use the ORIGINAL
consultation as source of truth.

Keep the diarization judgment and clinical-note judgment
separate in the explanations.
"""


# ============================================================
# AI EVALUATION
# ============================================================

def evaluate_case(
    case_id: str,
) -> CaseEvaluation:
    """Evaluate one stored consultation case."""

    oracle = load_oracle(
        case_id
    )

    transcription = (
        load_diarized_transcription(
            case_id
        )
    )

    generated_note = (
        load_generated_note(
            case_id
        )
    )

    expected_dialogue = (
        create_expected_dialogue(
            oracle
        )
    )

    evaluation_input = {
        "case_id":
            case_id,

        "scenario":
            oracle.get(
                "scenario",
                "",
            ),

        "product_speaker_model": {
            "doctor_output_label":
                "Læge",

            "patient_side_output_label":
                "Patient",

            "patient_side_source_roles": [
                "patient",
                "parent",
                "child",
                "spouse",
                "caregiver",
                "family",
            ],
        },

        "ground_truth_expected_facts":
            oracle.get(
                "expected_facts",
                {},
            ),

        "ground_truth_speaker_facts":
            oracle.get(
                "speaker_facts",
                {},
            ),

        "ground_truth_dialogue":
            expected_dialogue,

        "actual_diarized_transcription":
            transcription,

        "generated_clinical_note":
            generated_note,
    }

    print()
    print("=" * 80)
    print(
        f"EVALUATING {case_id}"
    )
    print("=" * 80)

    response = (
        client.responses.parse(
            model=MODEL,

            reasoning={
                "effort": "medium",
            },

            input=[
                {
                    "role": "system",
                    "content":
                        SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content":
                        json.dumps(
                            evaluation_input,
                            indent=2,
                            ensure_ascii=False,
                        ),
                },
            ],

            text_format=(
                CaseEvaluation
            ),
        )
    )

    result = (
        response.output_parsed
    )

    if result is None:
        raise RuntimeError(
            f"{case_id}: model returned "
            "no parsed evaluation."
        )

    # --------------------------------------------------------
    # FORCE SOURCE IDENTIFIERS
    # --------------------------------------------------------

    result.case_id = (
        case_id
    )

    result.scenario = str(
        oracle.get(
            "scenario",
            "",
        )
    )

    # --------------------------------------------------------
    # DETERMINISTIC DIARIZATION SCORE
    # --------------------------------------------------------
    #
    # IMPORTANT:
    # Do NOT trust the model's overall_score/verdict.
    #
    # The model evaluates the component scores.
    # Python calculates the final score consistently.
    # --------------------------------------------------------

    result.overall_score = (
        calculate_diarization_overall(
            attribution=(
                result.overall_attribution_score
            ),
            content=(
                result.content_retention_score
            ),
            integrity=(
                result.hallucination_score
            ),
        )
    )

    result.verdict = (
        calculate_verdict(
            result.overall_score
        )
    )

    return result


# ============================================================
# SAVE PER-CASE RESULT
# ============================================================

def save_case_result(
    result: CaseEvaluation,
) -> None:
    """Save complete structured result for one case."""

    EVALUATION_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    case_file = (
        EVALUATION_ROOT
        / f"{result.case_id}.json"
    )

    case_file.write_text(
        result.model_dump_json(
            indent=2
        ),
        encoding="utf-8",
    )


# ============================================================
# PRINT ONE CASE
# ============================================================

def print_case_result(
    result: CaseEvaluation,
) -> None:
    """Print detailed human-readable evaluation."""

    print()

    print("-" * 80)
    print("DIARIZATION / TRANSCRIPTION")
    print("-" * 80)

    print(
        f"Content retention:          "
        f"{result.content_retention_score}%"
    )

    print(
        f"Doctor attribution:         "
        f"{result.doctor_attribution_score}%"
    )

    print(
        f"Patient-side attribution:   "
        f"{result.patient_side_attribution_score}%"
    )

    print(
        f"Overall attribution:        "
        f"{result.overall_attribution_score}%"
    )

    print(
        f"Transcription integrity:    "
        f"{result.hallucination_score}%"
    )

    print(
        f"Diarization overall:        "
        f"{result.overall_score}%"
    )

    print(
        f"Verdict:                    "
        f"{result.verdict.upper()}"
    )

    print()

    print(
        f"Expected source turns:      "
        f"{result.expected_turn_count}"
    )

    print(
        f"Evaluated source turns:     "
        f"{result.evaluated_turn_count}"
    )

    print(
        f"Correctly attributed:       "
        f"{result.correctly_attributed_turns}"
    )

    print(
        f"Misattributed turns:        "
        f"{result.misattributed_turns}"
    )

    print(
        f"Missing turns:              "
        f"{result.missing_turns}"
    )

    if result.attribution_errors:

        print()
        print(
            "Attribution errors:"
        )

        for error in (
            result.attribution_errors
        ):
            print(
                f"  - source role: "
                f"{error.source_role}"
            )

            print(
                f"    source: "
                f"{error.source_text}"
            )

            if error.observed_text:
                print(
                    f"    observed: "
                    f"{error.observed_text}"
                )

            print(
                f"    expected="
                f"{error.expected_bucket}, "
                f"actual="
                f"{error.actual_bucket}"
            )

            print(
                f"    reason: "
                f"{error.explanation}"
            )

    if result.missing_content:

        print()
        print(
            "Missing transcription content:"
        )

        for item in (
            result.missing_content
        ):
            print(
                f"  - [{item.source_role}] "
                f"{item.source_text}"
            )

            print(
                f"    {item.explanation}"
            )

    if result.hallucinated_content:

        print()
        print(
            "Unsupported transcription content:"
        )

        for item in (
            result.hallucinated_content
        ):
            print(
                f"  - {item.observed_text}"
            )

            print(
                f"    bucket="
                f"{item.assigned_bucket}"
            )

            print(
                f"    {item.explanation}"
            )

    # ========================================================
    # CLINICAL NOTE
    # ========================================================

    print()
    print("-" * 80)
    print("GENERATED CLINICAL NOTE")
    print("-" * 80)

    print(
        f"Clinical fact retention:    "
        f"{result.clinical_fact_retention_score}%"
    )

    print(
        f"Clinical note fidelity:     "
        f"{result.clinical_note_fidelity_score}%"
    )

    print(
        f"Clinical hallucination "
        f"integrity: "
        f"{result.clinical_note_hallucination_score}%"
    )

    print(
        f"Missing clinical facts:     "
        f"{len(result.clinically_missing_facts)}"
    )

    print(
        f"Invented clinical facts:    "
        f"{len(result.clinically_invented_facts)}"
    )

    if result.clinically_missing_facts:

        print()
        print(
            "Missing clinical facts:"
        )

        for fact in (
            result.clinically_missing_facts
        ):
            print(
                f"  - {fact}"
            )

    else:
        print()
        print(
            "Missing clinical facts: none"
        )

    if result.clinically_invented_facts:

        print()
        print(
            "Unsupported/invented "
            "clinical facts:"
        )

        for fact in (
            result.clinically_invented_facts
        ):
            print(
                f"  - {fact}"
            )

    else:
        print()
        print(
            "Unsupported/invented "
            "clinical facts: none"
        )

    print()
    print(
        "Clinical note assessment:"
    )

    print(
        result.clinical_note_summary
    )

    # ========================================================
    # OVERALL SUMMARY
    # ========================================================

    print()
    print("-" * 80)
    print("CASE INTERPRETATION")
    print("-" * 80)

    print(
        result.summary
    )


# ============================================================
# FINAL AGGREGATE REPORT
# ============================================================

def save_summary(
    results: list[
        CaseEvaluation
    ],
) -> None:
    """Create machine-readable + human-readable final reports."""

    EVALUATION_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # DIARIZATION AVERAGES
    # --------------------------------------------------------

    avg_content = mean(
        result.content_retention_score
        for result in results
    )

    avg_doctor = mean(
        result.doctor_attribution_score
        for result in results
    )

    avg_patient = mean(
        result.patient_side_attribution_score
        for result in results
    )

    avg_attribution = mean(
        result.overall_attribution_score
        for result in results
    )

    avg_transcription_integrity = mean(
        result.hallucination_score
        for result in results
    )

    avg_diarization_overall = mean(
        result.overall_score
        for result in results
    )

    # --------------------------------------------------------
    # NOTE AVERAGES
    # --------------------------------------------------------

    avg_clinical_retention = mean(
        result.clinical_fact_retention_score
        for result in results
    )

    avg_clinical_fidelity = mean(
        result.clinical_note_fidelity_score
        for result in results
    )

    avg_clinical_hallucination = mean(
        result.clinical_note_hallucination_score
        for result in results
    )

    # --------------------------------------------------------
    # COUNTS
    # --------------------------------------------------------

    verdict_counts = {
        "excellent": 0,
        "good": 0,
        "degraded": 0,
        "poor": 0,
    }

    total_misattributed = 0
    total_missing_turns = 0

    total_missing_clinical_facts = 0
    total_invented_clinical_facts = 0

    for result in results:

        verdict_counts[
            result.verdict
        ] += 1

        total_misattributed += (
            result.misattributed_turns
        )

        total_missing_turns += (
            result.missing_turns
        )

        total_missing_clinical_facts += (
            len(
                result.clinically_missing_facts
            )
        )

        total_invented_clinical_facts += (
            len(
                result.clinically_invented_facts
            )
        )

    # --------------------------------------------------------
    # GROUP BY ORIGINAL SOURCE SPEAKER COUNT
    # --------------------------------------------------------

    speaker_groups: dict[
        int,
        list[CaseEvaluation],
    ] = {}

    for result in results:

        oracle = load_oracle(
            result.case_id
        )

        speaker_count = int(
            oracle.get(
                "speaker_count",
                0,
            )
        )

        speaker_groups.setdefault(
            speaker_count,
            [],
        ).append(
            result
        )

    group_summary = {}

    for (
        speaker_count,
        group,
    ) in sorted(
        speaker_groups.items()
    ):

        group_summary[
            str(
                speaker_count
            )
        ] = {
            "cases":
                len(group),

            "average_content_retention":
                round(
                    mean(
                        item.content_retention_score
                        for item in group
                    ),
                    2,
                ),

            "average_doctor_attribution":
                round(
                    mean(
                        item.doctor_attribution_score
                        for item in group
                    ),
                    2,
                ),

            "average_patient_side_attribution":
                round(
                    mean(
                        item.patient_side_attribution_score
                        for item in group
                    ),
                    2,
                ),

            "average_attribution":
                round(
                    mean(
                        item.overall_attribution_score
                        for item in group
                    ),
                    2,
                ),

            "average_diarization_overall":
                round(
                    mean(
                        item.overall_score
                        for item in group
                    ),
                    2,
                ),

            "average_clinical_fact_retention":
                round(
                    mean(
                        item.clinical_fact_retention_score
                        for item in group
                    ),
                    2,
                ),

            "average_clinical_note_fidelity":
                round(
                    mean(
                        item.clinical_note_fidelity_score
                        for item in group
                    ),
                    2,
                ),

            "average_clinical_note_hallucination_integrity":
                round(
                    mean(
                        item.clinical_note_hallucination_score
                        for item in group
                    ),
                    2,
                ),
        }

    # --------------------------------------------------------
    # MACHINE-READABLE SUMMARY
    # --------------------------------------------------------

    summary = {
        "model":
            MODEL,

        "cases_evaluated":
            len(results),

        "scoring": {
            "diarization_overall_formula":
                (
                    "55% overall attribution + "
                    "35% content retention + "
                    "10% transcription integrity"
                ),

            "verdict_thresholds": {
                "excellent":
                    "95-100",

                "good":
                    "85-94",

                "degraded":
                    "65-84",

                "poor":
                    "0-64",
            },
        },

        "diarization": {
            "average_content_retention":
                round(
                    avg_content,
                    2,
                ),

            "average_doctor_attribution":
                round(
                    avg_doctor,
                    2,
                ),

            "average_patient_side_attribution":
                round(
                    avg_patient,
                    2,
                ),

            "average_overall_attribution":
                round(
                    avg_attribution,
                    2,
                ),

            "average_transcription_integrity":
                round(
                    avg_transcription_integrity,
                    2,
                ),

            "average_overall_score":
                round(
                    avg_diarization_overall,
                    2,
                ),

            "total_misattributed_turns":
                total_misattributed,

            "total_missing_turns":
                total_missing_turns,

            "verdict_counts":
                verdict_counts,
        },

        "clinical_note": {
            "average_fact_retention":
                round(
                    avg_clinical_retention,
                    2,
                ),

            "average_fidelity":
                round(
                    avg_clinical_fidelity,
                    2,
                ),

            "average_hallucination_integrity":
                round(
                    avg_clinical_hallucination,
                    2,
                ),

            "total_missing_clinical_facts":
                total_missing_clinical_facts,

            "total_invented_clinical_facts":
                total_invented_clinical_facts,
        },

        "by_original_speaker_count":
            group_summary,

        "case_results": [
            {
                "case_id":
                    item.case_id,

                "scenario":
                    item.scenario,

                "diarization": {
                    "content_retention":
                        item.content_retention_score,

                    "doctor_attribution":
                        item.doctor_attribution_score,

                    "patient_side_attribution":
                        item.patient_side_attribution_score,

                    "overall_attribution":
                        item.overall_attribution_score,

                    "transcription_integrity":
                        item.hallucination_score,

                    "overall":
                        item.overall_score,

                    "misattributed_turns":
                        item.misattributed_turns,

                    "missing_turns":
                        item.missing_turns,

                    "verdict":
                        item.verdict,
                },

                "clinical_note": {
                    "fact_retention":
                        item.clinical_fact_retention_score,

                    "fidelity":
                        item.clinical_note_fidelity_score,

                    "hallucination_integrity":
                        item.clinical_note_hallucination_score,

                    "missing_fact_count":
                        len(
                            item.clinically_missing_facts
                        ),

                    "invented_fact_count":
                        len(
                            item.clinically_invented_facts
                        ),
                },
            }

            for item in results
        ],
    }

    summary_file = (
        EVALUATION_ROOT
        / "evaluation-summary.json"
    )

    summary_file.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # HUMAN-READABLE REPORT
    # --------------------------------------------------------

    lines = [
        "=" * 100,
        "PEOPLE'S CLINIC DIARIZATION + CLINICAL NOTE AI EVALUATION",
        "=" * 100,
        "",
        f"Model: {MODEL}",
        f"Cases evaluated: {len(results)}",
        "",
        "DIARIZATION SCORING",
        "-" * 100,
        (
            "Overall score = "
            "55% attribution + "
            "35% content retention + "
            "10% transcription integrity"
        ),
        (
            "Verdicts: "
            "Excellent 95-100 | "
            "Good 85-94 | "
            "Degraded 65-84 | "
            "Poor 0-64"
        ),
        "",
        "DIARIZATION / TRANSCRIPTION",
        "-" * 100,
        (
            "Average content retention:           "
            f"{avg_content:.1f}%"
        ),
        (
            "Average doctor attribution:          "
            f"{avg_doctor:.1f}%"
        ),
        (
            "Average patient-side attribution:    "
            f"{avg_patient:.1f}%"
        ),
        (
            "Average overall attribution:         "
            f"{avg_attribution:.1f}%"
        ),
        (
            "Average transcription integrity:     "
            f"{avg_transcription_integrity:.1f}%"
        ),
        (
            "Average diarization overall:         "
            f"{avg_diarization_overall:.1f}%"
        ),
        "",
        (
            "Total misattributed source turns:    "
            f"{total_misattributed}"
        ),
        (
            "Total missing source turns:          "
            f"{total_missing_turns}"
        ),
        "",
        "DIARIZATION VERDICTS",
        "-" * 100,
        (
            "Excellent: "
            f"{verdict_counts['excellent']}"
        ),
        (
            "Good:      "
            f"{verdict_counts['good']}"
        ),
        (
            "Degraded:  "
            f"{verdict_counts['degraded']}"
        ),
        (
            "Poor:      "
            f"{verdict_counts['poor']}"
        ),
        "",
        "GENERATED CLINICAL NOTE",
        "-" * 100,
        (
            "Average clinical fact retention:     "
            f"{avg_clinical_retention:.1f}%"
        ),
        (
            "Average clinical note fidelity:      "
            f"{avg_clinical_fidelity:.1f}%"
        ),
        (
            "Average hallucination integrity:     "
            f"{avg_clinical_hallucination:.1f}%"
        ),
        "",
        (
            "Total missing clinical facts:        "
            f"{total_missing_clinical_facts}"
        ),
        (
            "Total unsupported clinical facts:    "
            f"{total_invented_clinical_facts}"
        ),
        "",
        "RESULTS BY ORIGINAL SOURCE SPEAKER COUNT",
        "-" * 100,
    ]

    for (
        speaker_count,
        group,
    ) in group_summary.items():

        lines.append(
            f"{speaker_count} source speakers: "
            f"{group['cases']} cases | "
            f"content="
            f"{group['average_content_retention']:.1f}% | "
            f"attribution="
            f"{group['average_attribution']:.1f}% | "
            f"diarization="
            f"{group['average_diarization_overall']:.1f}% | "
            f"note-retention="
            f"{group['average_clinical_fact_retention']:.1f}% | "
            f"note-fidelity="
            f"{group['average_clinical_note_fidelity']:.1f}% | "
            f"note-safety="
            f"{group['average_clinical_note_hallucination_integrity']:.1f}%"
        )

    lines.extend(
        [
            "",
            "CASE RESULTS",
            "-" * 100,
        ]
    )

    for result in results:

        lines.append(
            f"{result.case_id:<10} "
            f"content="
            f"{result.content_retention_score:>3}%  "
            f"attr="
            f"{result.overall_attribution_score:>3}%  "
            f"diar="
            f"{result.overall_score:>3}%  "
            f"{result.verdict.upper():<9}  "
            f"note-ret="
            f"{result.clinical_fact_retention_score:>3}%  "
            f"note-fid="
            f"{result.clinical_note_fidelity_score:>3}%  "
            f"note-safe="
            f"{result.clinical_note_hallucination_score:>3}%"
        )

    lines.extend(
        [
            "",
            "=" * 100,
        ]
    )

    report_file = (
        EVALUATION_ROOT
        / "evaluation-report.txt"
    )

    report_file.write_text(
        "\n".join(
            lines
        ),
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # PRINT FINAL REPORT
    # --------------------------------------------------------

    print()
    print(
        "\n".join(
            lines
        )
    )

    print()

    print(
        f"JSON summary -> "
        f"{summary_file}"
    )

    print(
        f"Text report  -> "
        f"{report_file}"
    )


# ============================================================
# MAIN
# ============================================================

def main():
    """Evaluate all configured cases."""

    EVALUATION_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    results: list[
        CaseEvaluation
    ] = []

    failed_cases: list[
        tuple[str, str]
    ] = []

    print()
    print("=" * 80)
    print(
        "PEOPLE'S CLINIC AI EVALUATION"
    )
    print("=" * 80)

    print(
        f"Model: {MODEL}"
    )

    print(
        f"Cases requested: "
        f"{len(CASE_IDS)}"
    )

    print(
        f"Oracle root: "
        f"{CASES_ROOT}"
    )

    print(
        f"Results root: "
        f"{RESULTS_ROOT}"
    )

    for case_id in CASE_IDS:

        try:

            result = evaluate_case(
                case_id
            )

            save_case_result(
                result
            )

            print_case_result(
                result
            )

            results.append(
                result
            )

        except Exception as exc:

            message = (
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            failed_cases.append(
                (
                    case_id,
                    message,
                )
            )

            print()
            print("=" * 80)

            print(
                f"{case_id}: "
                "EVALUATION FAILED"
            )

            print("=" * 80)

            print(
                message
            )

    # --------------------------------------------------------
    # NO SUCCESSFUL CASES
    # --------------------------------------------------------

    if not results:
        raise RuntimeError(
            "No cases were successfully evaluated."
        )

    # --------------------------------------------------------
    # SAVE SUCCESSFUL SUMMARY
    # --------------------------------------------------------

    save_summary(
        results
    )

    # --------------------------------------------------------
    # PRINT EVALUATION FAILURES
    # --------------------------------------------------------

    if failed_cases:

        print()
        print("=" * 80)
        print(
            "AI EVALUATION FAILURES"
        )
        print("=" * 80)

        for (
            case_id,
            message,
        ) in failed_cases:

            print(
                f"{case_id}: "
                f"{message}"
            )

        print()

        print(
            f"Successful evaluations: "
            f"{len(results)}"
        )

        print(
            f"Failed evaluations: "
            f"{len(failed_cases)}"
        )

    else:

        print()
        print("=" * 80)

        print(
            "ALL REQUESTED CASES "
            "EVALUATED SUCCESSFULLY"
        )

        print("=" * 80)


if __name__ == "__main__":
    main()
