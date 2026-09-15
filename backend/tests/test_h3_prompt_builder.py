from core.logic.prompt_builder import build_h3_video_prompt, inject_h3_camera_direction


def test_i2v_prompt_keeps_alignment_and_native_section_order():
    prompt = build_h3_video_prompt(
        user_prompt="A woman continues walking through the glasshouse.",
        mode="i2v",
        duration_seconds=5.17,
        scene_context="Blue-hour glasshouse, cyan practical lights",
        shot_assets=[{"asset_name": "Mara", "role": "character"}],
        has_first_frame=True,
    )

    assert prompt.startswith("For the target video, at 0.00 seconds")
    assert prompt.index("integrated_multimodal_description:") < prompt.index("overall_soundscape:")
    assert prompt.index("overall_soundscape:") < prompt.index("non_diegetic_music:")
    assert "Continuity ledger: Mara (character)" in prompt
    assert "no silence gap" in prompt


def test_ref2va_prompt_describes_image_video_and_audio_retention():
    prompt = build_h3_video_prompt(
        user_prompt="Continue the same performance without replaying the cut.",
        mode="r2v",
        duration_seconds=5,
        reference_image_count=2,
        has_reference_video=True,
        has_reference_audio=True,
    )

    assert prompt.startswith("subject_definitions:")
    assert "<Picture 2>" in prompt
    assert "<Video 1>" in prompt
    assert "<Audio 1>" in prompt
    assert "without replaying its ending" in prompt


def test_camera_direction_stays_inside_h3_description():
    source = build_h3_video_prompt("A calm walk.", "i2v", 5, has_first_frame=True)
    result = inject_h3_camera_direction(source, "slow dolly forward")

    description = result.split("integrated_multimodal_description:", 1)[1].split("overall_soundscape:", 1)[0]
    assert "slow dolly forward" in description
    assert result.rstrip().endswith("across edits.")
