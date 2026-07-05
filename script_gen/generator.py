#!/usr/bin/env python3
"""
Script generation engine for the social media agent.
Generates YouTube video scripts via template filling (simulating LLM).
"""

import sys
import os
import json
import time
import argparse
from typing import Dict, List, Any, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from config import CHANNELS
import templates


def generate_script(channel: str, topic: str) -> Dict[str, Any]:
    """Generate a script with retry logic and exponential backoff."""
    max_attempts = 3
    base_delay = 1
    
    for attempt in range(max_attempts):
        try:
            start_time = time.time()
            script = _generate_script_from_template(channel, topic)
            elapsed = time.time() - start_time
            if elapsed > 60:
                raise Exception("Generation timeout exceeded 60s")
            return script
        except Exception as e:
            if attempt == max_attempts - 1:
                raise e
            delay = base_delay * (2 ** attempt)
            print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...", file=sys.stderr)
            time.sleep(delay)
    
    raise Exception("Failed to generate script after all attempts")


def _generate_script_from_template(channel: str, topic: str) -> Dict[str, Any]:
    """
    Generate script from template by filling in placeholders.
    """
    # Get the template for the channel
    scene_templates = templates.get_template(channel)
    if not scene_templates:
        # Fallback to default template
        scene_templates = templates.get_default_template()
    
    scenes = []
    for idx, scene_template in enumerate(scene_templates, start=1):
        # Fill in the placeholders
        description = scene_template["description"].format(topic=topic)
        visual_cue = scene_template["visual_cue"].format(topic=topic)
        voiceover_text = scene_template["voiceover_text"].format(topic=topic)
        
        scene = {
            "scene_number": idx,
            "description": description,
            "duration_seconds": scene_template["duration_seconds"],
            "visual_cue": visual_cue,
            "voiceover_text": voiceover_text
        }
        scenes.append(scene)
    
    # Ensure at least 3 scenes (should already be satisfied by our templates)
    if len(scenes) < 3:
        # Pad with default scenes if needed
        while len(scenes) < 3:
            scenes.append({
                "scene_number": len(scenes) + 1,
                "description": f"Additional context on {topic}.",
                "duration_seconds": 30,
                "visual_cue": f"Visuals related to {topic}.",
                "voiceover_text": f"More insights on {topic}."
            })
    
    return {"scenes": scenes}


def main():
    parser = argparse.ArgumentParser(description="Generate YouTube video script for a social media channel.")
    parser.add_argument("--channel", required=True, help="Channel key (e.g., soccer, christian, trading)")
    parser.add_argument("--topic", required=True, help="Topic for the video script")
    parser.add_argument("--output", help="Output file path for JSON script (if not provided, prints to stdout)")
    
    args = parser.parse_args()
    
    try:
        script = generate_script(args.channel, args.topic)
        json_output = json.dumps(script, indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(json_output)
            print(f"Script written to {args.output}", file=sys.stderr)
        else:
            print(json_output)
    except Exception as e:
        print(f"Error generating script: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
