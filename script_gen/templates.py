"""
Per-channel script prompt templates for the social media agent.
"""

from typing import List, Dict, Any

# Template structure for each channel
# Each template is a list of scenes, each scene is a dict with:
#   scene_number: int (will be overridden by generator to be sequential)
#   description: str (with {topic} placeholder)
#   duration_seconds: int (target duration for the scene)
#   visual_cue: str (with {topic} placeholder)
#   voiceover_text: str (with {topic} placeholder)

CHANNEL_TEMPLATES = {
    "soccer": [
        {
            "scene_number": 1,
            "description": "Introduction to the {topic} match, setting the stage and key stakes.",
            "duration_seconds": 30,
            "visual_cue": "Montage of recent clips from the {topic} teams, stadium exterior, fans arriving.",
            "voiceover_text": "Welcome to today's analysis of the {topic}! We're breaking down what you need to know before kickoff."
        },
        {
            "scene_number": 2,
            "description": "Tactical analysis of both teams' formations and key players to watch in the {topic}.",
            "duration_seconds": 60,
            "visual_cue": "Animated tactical board showing team formations, player heat maps, and key zones.",
            "voiceover_text": "In the {topic}, expect Team A to push high while Team B looks to counter. Key player X could be the difference maker."
        },
        {
            "scene_number": 3,
            "description": "Highlight reel of the best moments from the {topic} and what they mean for the season.",
            "duration_seconds": 45,
            "visual_cue": "Fast-cut highlights of goals, saves, and tackles from the {topic} match with slow-mo replays.",
            "voiceover_text": "Those were the defining moments of the {topic}! Let's see how this result impacts the league table."
        },
        {
            "scene_number": 4,
            "description": "Post-match analysis and predictions for upcoming fixtures based on the {topic} outcome.",
            "duration_seconds": 45,
            "visual_cue": "Analyst desk with graphics showing league table, upcoming fixtures, and player ratings.",
            "voiceover_text": "Looking ahead, the {topic} result means Team A must win next week to stay in contention."
        }
    ],
    "christian": [
        {
            "scene_number": 1,
            "description": "Opening reflection on the {topic} theme, connecting scripture to daily life.",
            "duration_seconds": 40,
            "visual_cue": "Warm lighting, host in a comfortable setting with a Bible and candles.",
            "voiceover_text": "Today we dive into the {topic}, exploring how this timeless truth applies to our walk with God."
        },
        {
            "scene_number": 2,
            "description": "Bible study deep dive: key passages related to the {topic} and their historical context.",
            "duration_seconds": 70,
            "visual_cue": "On-screen Bible verses, maps of ancient Israel, and artwork illustrating the story.",
            "voiceover_text": "Let's look at what Scripture says about the {topic}. In [Book] chapter [verse], we see God's heart for..."
        },
        {
            "scene_number": 3,
            "description": "Personal application: how to live out the {topic} in practical ways this week.",
            "duration_seconds": 50,
            "visual_cue": "Host journaling, footage of people serving in community, split-screen of daily routines.",
            "voiceover_text": "The {topic} isn't just theoretical—it changes how we treat others, handle work, and rest in God's grace."
        }
    ],
    "trading": [
        {
            "scene_number": 1,
            "description": "Market overview: setting the context for the {topic} in today's trading environment.",
            "duration_seconds": 35,
            "visual_cue": "Financial news ticker, charts of major indices, and heat map of sector performance.",
            "voiceover_text": "Welcome to our deep dive on the {topic}. First, let's see where the market stands today."
        },
        {
            "scene_number": 2,
            "description": "Strategy breakdown: explaining the {topic} approach, entry/exit rules, and risk management.",
            "duration_seconds": 80,
            "visual_cue": "Animated strategy flowchart, candlestick charts showing examples, and risk/reward diagrams.",
            "voiceover_text": "The {topic} works by identifying [condition]. We enter when [signal], place stops at [level], and target [target]."
        },
        {
            "scene_number": 3,
            "description": "Live trade example or historical backtest of the {topic} demonstrating effectiveness.",
            "duration_seconds": 60,
            "visual_cue": "Screen capture of trading platform, trade journal entries, and equity curve graph.",
            "voiceover_text": "Here's a recent example of the {topic} in action: we saw [setup], took the trade, and achieved [result]."
        }
    ]
}

def get_template(channel: str) -> List[Dict[str, Any]]:
    """
    Get the scene template for a given channel.
    Returns a list of scene dictionaries.
    """
    return CHANNEL_TEMPLATES.get(channel, [])

def get_default_template() -> List[Dict[str, Any]]:
    """
    Return a generic template if channel not found.
    """
    return [
        {
            "scene_number": 1,
            "description": "Introduction to {topic}.",
            "duration_seconds": 30,
            "visual_cue": "Opening visuals related to {topic}.",
            "voiceover_text": "Welcome to our discussion on {topic}."
        },
        {
            "scene_number": 2,
            "description": "Main points about {topic}.",
            "duration_seconds": 60,
            "visual_cue": "Illustrations and examples of {topic}.",
            "voiceover_text": "Let's explore the key aspects of {topic}."
        },
        {
            "scene_number": 3,
            "description": "Conclusion and call to action for {topic}.",
            "duration_seconds": 30,
            "visual_cue": "Closing visuals and summary of {topic}.",
            "voiceover_text": "Thanks for watching! Don't forget to like and subscribe for more on {topic}."
        }
    ]
