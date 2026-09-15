"""
Prompt Builder - Model-aware prompt compilation.

Builds effective prompts for image and video generation, choosing between
a flat format (for Qwen/LTX/Fal models) and a structured format (for MiniMax H3).

The flat format is a simple string concatenation of scene context, character
names, camera angle tags, and the user's action prompt.

The H3 structured format produces named sections per the MiniMax H3 prompt guide:
  - subject_definitions
  - summary
  - retention_analysis
  - detailed_description
  - overall_soundscape
  - non_diegetic_music
"""

import re
from typing import Optional, List, Dict, Any, Tuple


_H3_SECTION_RE = re.compile(
    r"(?ms)^([a-z_]+):\s*\n?(.*?)(?=^[a-z_]+:\s*$|\Z)"
)


def _h3_sections(prompt: str) -> Dict[str, str]:
    return {
        match.group(1): match.group(2).strip()
        for match in _H3_SECTION_RE.finditer(prompt or "")
    }


def inject_h3_camera_direction(prompt: str, camera_direction: str) -> str:
    """Insert camera direction inside an H3 section instead of after the schema."""
    if not camera_direction or camera_direction in prompt:
        return prompt
    field = "detailed_description" if "detailed_description:" in prompt else "integrated_multimodal_description"
    marker = f"{field}:"
    if marker not in prompt:
        return f"{prompt}, {camera_direction}"
    before, after = prompt.split(marker, 1)
    next_section = re.search(r"(?m)^([a-z_]+):\s*$", after)
    if next_section:
        body = after[:next_section.start()].rstrip()
        tail = after[next_section.start():]
        return f"{before}{marker}{body} Camera direction: {camera_direction}.\n{tail}"
    return f"{before}{marker}{after.rstrip()} Camera direction: {camera_direction}."


def build_h3_video_prompt(
    user_prompt: str,
    mode: str,
    duration_seconds: float,
    scene_context: str = "",
    shot_assets: Optional[List[Dict[str, Any]]] = None,
    reference_image_count: int = 0,
    has_reference_video: bool = False,
    has_reference_audio: bool = False,
    has_first_frame: bool = False,
    has_last_frame: bool = False,
    soundscape: Optional[str] = None,
    music: Optional[str] = None,
) -> str:
    """Compile an H3-native prompt with explicit cross-shot continuity rules."""
    shot_assets = shot_assets or []
    parsed = _h3_sections(user_prompt)
    raw_description = (
        parsed.get("detailed_description")
        or parsed.get("integrated_multimodal_description")
        or parsed.get("summary")
        or user_prompt.strip()
    )
    identity_parts = []
    for asset in shot_assets:
        role = asset.get("role", asset.get("asset_type", ""))
        name = asset.get("asset_name", "").strip()
        if name and role in {"character", "location", "prop", "vehicle", "style"}:
            identity_parts.append(f"{name} ({role})")
    ledger = ", ".join(identity_parts)
    continuity = (
        "Preserve character identity, face geometry, hairstyle, wardrobe, props, set layout, "
        "light direction, color palette, screen direction and action momentum across the whole clip. "
        "Begin with the exact pose and composition supplied by the preceding boundary reference. "
        "Do not reset staging, lighting, ambience or performance at an internal shot boundary."
    )
    description_parts = [part for part in (scene_context.strip(), raw_description, continuity) if part]
    if ledger:
        description_parts.append(f"Continuity ledger: {ledger}.")
    description = " ".join(description_parts)
    resolved_soundscape = soundscape or parsed.get("overall_soundscape") or (
        "One continuous 32 kHz stereo room tone with stable ambience, perspective and noise floor. "
        "Carry dialogue, breaths, footsteps and reverberation naturally across edits; no silence gap, "
        "impact sound, ambience restart or sudden gain change at a shot boundary."
    )
    resolved_music = music or parsed.get("non_diegetic_music") or (
        "No non-diegetic music unless explicitly requested; if present, keep one uninterrupted phrase "
        "with stable tempo, key and loudness across edits."
    )

    if mode.lower() == "r2v":
        subjects = []
        for index in range(reference_image_count):
            subjects.append(f"<Subject {index + 1}> is the identity and appearance shown in <Picture {index + 1}>.")
        if has_reference_video:
            subjects.append("<Video 1> defines the preceding motion, camera momentum, scene geometry and audio ambience.")
        if has_reference_audio:
            subjects.append("<Audio 1> defines the continuous voice, ambience and acoustic perspective.")
        subject_text = "\n".join(subjects) or "No external subject reference is supplied."
        retention = []
        if reference_image_count:
            retention.append("Fully preserve every referenced subject's identity, wardrobe, material and spatial role.")
        if has_reference_video:
            retention.append("Continue <Video 1> without replaying its ending; retain motion vectors, screen direction and room tone.")
        if has_reference_audio:
            retention.append("Use <Audio 1> as a continuous acoustic reference without a boundary reset.")
        return (
            f"subject_definitions:\n{subject_text}\n\n"
            f"summary:\nSeamless continuation: {raw_description}\n\n"
            f"retention_analysis:\n{' '.join(retention) or 'Retain the supplied scene state.'}\n\n"
            f"detailed_description:\n{description}\n\n"
            f"overall_soundscape:\n{resolved_soundscape}\n\n"
            f"non_diegetic_music:\n{resolved_music}"
        )[:4000]

    alignments = []
    if has_first_frame:
        alignments.append(
            "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced."
        )
    if has_last_frame:
        picture_number = 2 if has_first_frame else 1
        alignments.append(
            f"For the target video, at {duration_seconds:.2f} seconds into the target video, "
            f"<Picture {picture_number}> (from [Shot {picture_number}]) is fully referenced."
        )
    prefix = ("\n".join(alignments) + "\n\n") if alignments else ""
    return (
        f"{prefix}integrated_multimodal_description:\n{description}\n\n"
        f"overall_soundscape:\n{resolved_soundscape}\n\n"
        f"non_diegetic_music:\n{resolved_music}"
    )[:4000]


# Retention detail mapping — what "fully_preserved" means per asset type
RETAINED_DETAIL = {
    "character": "identity, face and clothing",
    "location": "layout, furnishing and lighting",
    "prop": "shape, colour and wear",
    "vehicle": "shape, colour and markings",
    "style": "palette, texture and grade",
    "effect": "shape, colour and behaviour",
}

# Audio retention markers
AUDIO_RETENTION_NOTES = {
    "fully_copy": "{label} is reused as the target video's complete final audio track.",
    "partially_copy": "part of {label} is copied; other sounds are added, removed or replaced.",
    "reference": "the target follows {label} without copying the original signal.",
    "weak_reference": "only a broad similarity to {label} in category and atmosphere is kept.",
}


def retention_note(label: str, marker: str, kind: Optional[str] = None) -> str:
    """Generate a human-readable retention instruction for a reference."""
    if marker == "fully_preserved":
        detail = RETAINED_DETAIL.get(kind or "")
        if detail:
            return f"the {detail} of {label} are retained."
        return f"{label} is retained as defined."
    elif marker == "partially_preserved":
        return f"{label} is still used, with some of its defined characteristics changed."
    elif marker == "attribute_transfer":
        return f"the characteristics of {label} are transferred to a different target subject."
    elif marker == "weak_reference":
        return f"only a broad similarity to {label} in style, category, composition and atmosphere is kept."
    return f"{label} is retained as defined."


def retention_enrichment_flat(name: str, role: str, retention: str) -> str:
    """Generate enrichment text for the flat prompt format based on retention level."""
    if retention == "fully_preserved":
        return f"featuring {name}"
    elif retention == "partially_preserved":
        return f"featuring {name}, with some characteristics changed"
    elif retention == "attribute_transfer":
        return f"transferring {name}'s characteristics to a different subject"
    elif retention == "weak_reference":
        return f"loosely referencing {name}'s style"
    return f"featuring {name}"


def build_flat_prompt(
    scene_context: str,
    prompt_enrichments: List[str],
    action_prefix: str,
    user_prompt: str,
    sks_tag: Optional[str] = None,
    is_pov: bool = False,
) -> str:
    """Build a flat prompt string (for Qwen/LTX/Fal models).

    This is the existing format: <sks> tag + scene context + enrichments + action + user prompt.
    """
    if is_pov:
        context_parts = []
        if scene_context:
            context_parts.append(scene_context)
        if prompt_enrichments:
            context_parts.append(", ".join(prompt_enrichments))
        if action_prefix:
            context_parts.append(action_prefix)
        context_str = ", ".join(context_parts)
        user_str = user_prompt.strip()
        if context_str and user_str:
            return f"{context_str}, {user_str}"
        return context_str or user_str

    parts = []
    if sks_tag:
        parts.append(sks_tag)
    elif not sks_tag:
        parts.append("wide establishing shot")

    context_parts = []
    if scene_context:
        context_parts.append(scene_context)
    if prompt_enrichments:
        context_parts.append(", ".join(prompt_enrichments))
    if action_prefix:
        context_parts.append(action_prefix)
    if context_parts:
        parts.append(", ".join(context_parts))
    if user_prompt.strip():
        parts.append(user_prompt.strip())

    return " ".join(parts)


def build_h3_structured_prompt(
    scene_context: str,
    shot_assets: List[Dict[str, Any]],
    asset_map: Dict[str, Dict[str, Any]],
    action_prefix: str,
    user_prompt: str,
    sks_tag: Optional[str] = None,
    is_pov: bool = False,
    soundscape: Optional[str] = None,
    music: Optional[str] = None,
    prev_character_ids: Optional[List[str]] = None,
) -> str:
    """Build a structured prompt for MiniMax H3.

    Produces named sections per the H3 prompt guide format.
    """
    prev_character_ids = prev_character_ids or []
    sections = []

    # --- Subject Definitions ---
    subject_lines = []
    picture_ordinal = 0
    subject_ordinal = 0
    subject_slots: Dict[str, Tuple[int, int]] = {}  # asset_id -> (subject_num, picture_num)

    for a in shot_assets:
        role = a.get("role", a.get("asset_type", ""))
        name = a.get("asset_name", "")
        asset_id = a.get("asset_id", "")
        img = a.get("image_path")
        retention = a.get("retention", "fully_preserved")
        full_asset = asset_map.get(asset_id, {})
        desc = full_asset.get("description", "")

        if not name:
            continue

        picture_ordinal += 1
        subject_ordinal += 1
        label = f"<Subject {subject_ordinal}>"
        pic_label = f"<Picture {picture_ordinal}>"
        subject_slots[asset_id] = (subject_ordinal, picture_ordinal)

        # Use description if name looks auto-generated
        display_name = name
        if name and "generated" in name.lower():
            display_name = desc if desc else name

        subject_lines.append(f"{label} is {display_name}, shown in {pic_label}.")

    if subject_lines:
        sections.append("subject_definitions:\n" + "\n".join(subject_lines))

    # --- Summary ---
    summary_parts = []
    if scene_context:
        summary_parts.append(scene_context)
    if sks_tag and not is_pov:
        summary_parts.append(sks_tag)
    if action_prefix:
        summary_parts.append(action_prefix)
    summary_parts.append(user_prompt.strip())
    sections.append("summary:\n" + ", ".join(summary_parts))

    # --- Retention Analysis ---
    retention_lines = []
    for a in shot_assets:
        name = a.get("asset_name", "")
        asset_id = a.get("asset_id", "")
        role = a.get("role", a.get("asset_type", ""))
        retention = a.get("retention", "fully_preserved")
        if not name:
            continue
        slot_info = subject_slots.get(asset_id)
        label = f"<Subject {slot_info[0]}>" if slot_info else name
        note = retention_note(label, retention, role)
        retention_lines.append(f"- {note}")
    if retention_lines:
        sections.append("retention_analysis:\n" + "\n".join(retention_lines))

    # --- Detailed Description ---
    desc_parts = []
    if scene_context:
        desc_parts.append(scene_context)
    if action_prefix:
        desc_parts.append(action_prefix)
    if sks_tag and not is_pov:
        desc_parts.append(sks_tag)
    if user_prompt.strip():
        desc_parts.append(user_prompt.strip())
    sections.append("detailed_description:\n" + ", ".join(desc_parts))

    # --- Overall Soundscape ---
    if soundscape:
        sections.append(f"overall_soundscape:\n{soundscape}")

    # --- Non-Diegetic Music ---
    if music:
        sections.append(f"non_diegetic_music:\n{music}")

    return "\n\n".join(sections)


def build_prompt(
    model_id: str,
    scene_context: str,
    shot_assets: List[Dict[str, Any]],
    asset_map: Dict[str, Dict[str, Any]],
    action_prefix: str,
    user_prompt: str,
    sks_tag: Optional[str] = None,
    is_pov: bool = False,
    is_establishing: bool = False,
    prompt_override: Optional[str] = None,
    soundscape: Optional[str] = None,
    music: Optional[str] = None,
    prev_character_ids: Optional[List[str]] = None,
) -> str:
    """Dispatch to the appropriate prompt builder based on model_id.

    If prompt_override is provided, it replaces the auto-compiled prompt entirely.
    """
    if prompt_override and prompt_override.strip():
        return prompt_override.strip()

    # Build enrichments from shot assets with retention awareness
    # Detect if the user's prompt focuses on a specific character by name.
    # If so, only include that character in enrichments and add a focus instruction
    # so the model doesn't force other characters into frame.
    user_prompt_lower = user_prompt.lower().strip()
    focused_character = None
    character_assets = []
    non_character_enrichments = []

    for a in shot_assets:
        role = a.get("role", a.get("asset_type", ""))
        name = a.get("asset_name", "")
        retention = a.get("retention", "fully_preserved")
        if not name:
            continue
        full_asset = asset_map.get(a.get("asset_id", ""), {})
        desc = full_asset.get("description", "")
        display_name = name
        if name and "generated" in name.lower():
            display_name = desc if desc else name
        if role == "character":
            character_assets.append((display_name, retention))
        elif role in ("prop", "vehicle"):
            non_character_enrichments.append(f"with {display_name}")

    # Check if user prompt mentions any character by name
    for display_name, retention in character_assets:
        name_lower = display_name.lower()
        # Match full name or first word (e.g. "pirate" in "Pirate Captain")
        name_words = name_lower.split()
        if name_lower in user_prompt_lower or (name_words and name_words[0] in user_prompt_lower):
            focused_character = display_name
            break

    prompt_enrichments = []
    if focused_character and not is_establishing:
        # User is focusing on a specific character — only include that one
        for display_name, retention in character_assets:
            if display_name == focused_character:
                prompt_enrichments.append(retention_enrichment_flat(display_name, "character", retention))
        prompt_enrichments.append(f"focus on {focused_character}, tight framing")
        prompt_enrichments.extend(non_character_enrichments)
    else:
        # Include all characters as before
        for display_name, retention in character_assets:
            prompt_enrichments.append(retention_enrichment_flat(display_name, "character", retention))
        prompt_enrichments.extend(non_character_enrichments)

    # H3 structured format
    if model_id == "minimax_h3":
        return build_h3_structured_prompt(
            scene_context=scene_context,
            shot_assets=shot_assets,
            asset_map=asset_map,
            action_prefix=action_prefix,
            user_prompt=user_prompt,
            sks_tag=sks_tag,
            is_pov=is_pov,
            soundscape=soundscape,
            music=music,
            prev_character_ids=prev_character_ids,
        )

    # Default: flat format
    return build_flat_prompt(
        scene_context=scene_context,
        prompt_enrichments=prompt_enrichments,
        action_prefix=action_prefix,
        user_prompt=user_prompt,
        sks_tag=sks_tag,
        is_pov=is_pov,
    )


# --- Dialogue Tag Parsing (for H3) ---

_DIALOGUE_TAG_RE = re.compile(r"@(\w[\w\s]*?)\s+says:\s*(.+?)(?=@\w[\w\s]*?\s+says:|$)", re.DOTALL)


def parse_dialogue_tags(prompt: str, shot_assets: List[Dict[str, Any]]) -> str:
    """Convert @character says: ... tags to H3 <Subject N> (SN) says, <d>[English] ...</d> format.

    Only applies when the model is MiniMax H3. Characters are matched by name
    to subject slots based on their order in shot_assets.
    """
    if not prompt or "@" not in prompt:
        return prompt

    # Build name -> subject slot mapping
    name_to_slot: Dict[str, int] = {}
    subject_ordinal = 0
    for a in shot_assets:
        role = a.get("role", a.get("asset_type", ""))
        name = a.get("asset_name", "")
        if not name or role != "character":
            continue
        subject_ordinal += 1
        name_to_slot[name.lower()] = subject_ordinal

    def replace_dialogue(match):
        name = match.group(1).strip()
        dialogue = match.group(2).strip()
        slot = name_to_slot.get(name.lower())
        if slot:
            s_label = f"S{slot}"
            return f"<Subject {slot}> ({s_label}) says, <d>[English] {dialogue}</d>"
        return match.group(0)

    return _DIALOGUE_TAG_RE.sub(replace_dialogue, prompt)
