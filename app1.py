from flask import Flask, request, jsonify, render_template
import os
import json
from openai import OpenAI
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from flask_cors import CORS
import random
import re

app = Flask(__name__)
CORS(app)
app.secret_key = os.urandom(24)  # Secret key for session management

load_dotenv()
# Configure OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# Load environment variables from .env file
# load_dotenv()

# Game state management
class GameState:
    def __init__(self):
        self.current_scene = "start"
        self.inventory = []
        self.player_stats = {"health": 100, "courage": 50, "wisdom": 50}
        self.visited_locations = []
        self.story_flags = {}
        self.story_context = (
            "You are the survivor of a catastrophic quantum breach. Now altered with unstable powers, "
            "you’ve been taken into SHIELD custody. Nick Fury believes you’re the only one who can stop "
            "a multiverse collapse — the fate of the Marvel Universe is in your hands."
        )
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_scene": self.current_scene,
            "inventory": self.inventory,
            "player_stats": self.player_stats,
            "visited_locations": self.visited_locations,
            "story_flags": self.story_flags,
            "story_context": self.story_context
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        self.current_scene = data.get("current_scene", "start")
        self.inventory = data.get("inventory", [])
        self.player_stats = data.get("player_stats", {"health": 100, "courage": 50, "wisdom": 50})
        self.visited_locations = data.get("visited_locations", [])
        self.story_flags = data.get("story_flags", {})
        self.story_context = data.get(
            "story_context",
            "You are the survivor of a catastrophic quantum breach. Now altered with unstable powers, "
            "you’ve been taken into SHIELD custody. Nick Fury believes you’re the only one who can stop "
            "a multiverse collapse — the fate of the Marvel Universe is in your hands."
        )


# Game session management
sessions = {}

# Base story framework with key waypoints
# This will be enhanced by AI-generated content
story_framework = {
    "start": {
        "description": "You awaken in a secure SHIELD bunker. You're told you were caught in a quantum reactor accident and are now exhibiting abilities no one fully understands. Nick Fury left a message: the world needs you.",
        "ai_prompt": "The protagonist awakens in a SHIELD bunker with newfound powers after a mysterious quantum accident. Nick Fury’s message urges them to prepare — something dangerous is brewing. Write a cinematic opening scene and offer 4 action-packed paths: test your powers, escape, contact Fury, or access the SHIELD mainframe."
    },

    "final_showdown": {
        "description": "The battle has reached Stark Tower. A multiverse breach is tearing reality, and the villain stands at its heart. Only you — with your powers and your choices — can stop the collapse.",
        "ai_prompt": "Atop Stark Tower, the multiverse breach expands. The villain harnesses unstable energy. The hero must act. Present 4 Marvel-style strategies: perhaps a sacrifice, a team-up, a tech gamble, or a morality test."
    },

    "tragic_ending": {
        "description": "You made the ultimate sacrifice. The multiverse is safe, but your light is gone. Your story echoes through timelines.",
        "ai_prompt": "The hero dies saving the multiverse. Write a powerful, emotional ending. Include reactions from iconic heroes and how the world remembers them."
    },

    "victorious_ending": {
        "description": "Against all odds, you closed the breach and stopped the villain. The Avengers salute you — the newest legend.",
        "ai_prompt": "The hero triumphs, saving the multiverse and proving themselves among the greats. Write a victorious Marvel-style ending with hints of new threats and growth."
    }
}


def generate_ai_content(prompt: str, temperature: float = 0.7) -> str:
    """Generate content using OpenAI's GPT-3.5 model"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Use the appropriate model
            messages=[
                {"role": "system", "content": "You are a cinematic narrator for a Marvel-style superhero adventure game called 'Marvel: Legacy Awakened'. Create action-packed, emotional, and immersive Marvel-like scenes. Let the player become a new hero in the Marvel Universe, interacting with elements like SHIELD, Stark tech, cosmic threats, and multiverse rifts. Make choices matter."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=800,
            top_p=1.0
        )
        return response.choices[0].message.content.strip()  # ✅ FIXED
    except Exception as e:
        print(f"Error calling OpenAI API: {str(e)}")
        return "The journey continues... (Error generating content, please try again)"


def generate_options(game_state: GameState, current_situation: str) -> List[Dict[str, str]]:
    """Generate 4 options plus the 'other' option using the AI"""
    
    # Create a context-aware prompt for the AI
    prompt = f"""
    In the superhero adventure game 'Marvel: Legacy Awakened':

    Current situation: {current_situation}

    Game state:
    - Current location: {game_state.current_scene}
    - Inventory: {', '.join(game_state.inventory) if game_state.inventory else 'empty'}
    - Player visited: {', '.join(game_state.visited_locations) if game_state.visited_locations else 'nowhere yet'}
    - Player stats: Health {game_state.player_stats.get('health')}, Courage {game_state.player_stats.get('courage')}, Wisdom {game_state.player_stats.get('wisdom')}
    - Story context: {game_state.story_context}

    Based on this Marvel-style situation, generate EXACTLY 4 dramatic, cinematic choices.

    Each choice must:
    1. Be under 15 words
    2. Feel heroic, risky, or clever
    3. Be meaningfully distinct
    4. Lead to a unique outcome or direction

    Format exactly like:
    1. Activate your repulsor cannon and blast the wall
    2. Hack the Stark console to access intel
    3. Call for backup using the SHIELD beacon
    4. Fly through the breach before it closes
"""

    
    try:
        options_text = generate_ai_content(prompt, temperature=0.8)
        
        # Process the AI-generated options
        options = []
        
        # Extract the numbered options from the AI response
        for line in options_text.split('\n'):
            match = re.match(r"^\d+[\.\:\)\-]\s+(.*)", line.strip())
            if match:
                option_text = match.group(1).strip()
                scene_id = "scene_" + "_".join(option_text.lower().split()[:3]).replace("'", "").replace('"', '')
                options.append({"text": option_text, "next_scene": scene_id})
        
        # Add the "Other" option where player can input their own choice
        options.append({"text": "Other (write your own action)", "next_scene": "custom_action"})
        
        # If we somehow don't have 5 options, generate a fallback set
        if len(options) < 5:
            options = [
                {"text": "Explore further ahead", "next_scene": "scene_explore_ahead"},
                {"text": "Examine your surroundings carefully", "next_scene": "scene_examine_surroundings"},
                {"text": "Rest and recover your strength", "next_scene": "scene_rest_recover"},
                {"text": "Try a different approach", "next_scene": "scene_different_approach"},
                {"text": "Other (write your own action)", "next_scene": "custom_action"}
            ]
        
        return options
    
    except Exception as e:
        print(f"Error generating options: {str(e)}")
        # Fallback options if AI generation fails
        return [
            {"text": "Continue forward cautiously", "next_scene": "scene_continue_forward"},
            {"text": "Look for an alternative path", "next_scene": "scene_alternative_path"},
            {"text": "Take a moment to think", "next_scene": "scene_think"},
            {"text": "Prepare for potential danger", "next_scene": "scene_prepare"},
            {"text": "Other (write your own action)", "next_scene": "custom_action"}
        ]
    
def generate_narrative(game_state: GameState, choice: str, ai_prompt: str) -> Dict[str, Any]:
    """
    Generate narrative and scene details using OpenAI's GPT model for Marvel-style superhero storytelling.
    """
    current_scene = game_state.current_scene
    visited = ", ".join(game_state.visited_locations) if game_state.visited_locations else "nowhere yet"
    items = ", ".join(game_state.inventory) if game_state.inventory else "nothing"

    # Create a detailed prompt for narrative generation
    prompt = f"""
    You are the storyteller for 'Marvel: Legacy Awakened', a cinematic superhero text adventure where the player takes on the role of a rising Marvel hero caught in a multiverse crisis.

    Current game state:
    - Current location: {current_scene}
    - Player has visited: {visited}
    - Player has in inventory: {items}
    - Player stats: Health {game_state.player_stats.get('health')}, Courage {game_state.player_stats.get('courage')}, Wisdom {game_state.player_stats.get('wisdom')}
    - Story context so far: {game_state.story_context}

    Player just chose: "{choice}"

    Additional context: {ai_prompt}

    Generate a thrilling continuation of the story (about 2-4 paragraphs) that:
    1. Reacts to the player's choice
    2. Describes what happens next in cinematic, vivid Marvel-style detail
    3. Builds tension and stakes fitting the superhero genre
    4. Keeps the story immersive and fast-paced

    Write in second person ("you") and present tense. Do NOT include choices at the end.
    """

    try:
        narrative_text = generate_ai_content(prompt)

        # Generate a short scene description
        description_prompt = f"""
        Based on this narrative, create a short scene description (max 3 sentences) that sets the stage visually:

        {narrative_text}

        The description should paint a clear Marvel-style cinematic moment.
        """
        scene_description = generate_ai_content(description_prompt, temperature=0.6)

        # Update story context
        context_prompt = f"""
        Summarize the following event in 1-2 sentences to add to the story context:

        Previous context: {game_state.story_context}
        New event: Player chose "{choice}" which led to: {narrative_text}
        """
        new_context = generate_ai_content(context_prompt, temperature=0.5)
        game_state.story_context += " " + new_context

        # Determine if this is an ending
        ending_prompt = f"""
        Does the following narrative represent the end of the adventure?

        Clues to look for:
        - Has the player saved or failed the mission?
        - Did they face final consequences or resolution?
        - Is this the climax or conclusion of their journey?

        Narrative: {narrative_text}
        Story context: {game_state.story_context}

        Respond with ONLY ONE word:
        - "continue"
        - "victory"
        - "defeat"
        """
        ending_decision = generate_ai_content(ending_prompt, temperature=0.4).strip().lower()

        is_ending = False
        ending_type = None
        if "victory" in ending_decision:
            ending_type = "victorious_ending"
            is_ending = True
        elif "defeat" in ending_decision:
            ending_type = "tragic_ending"
            is_ending = True

        # Generate options or final ending
        if is_ending:
            scene_data = story_framework.get(ending_type, {})
            ending_narrative = generate_ai_content(scene_data.get("ai_prompt", "Create a satisfying superhero ending."))
            return {
                "narrative": narrative_text + "\n\n" + ending_narrative,
                "scene_description": scene_description,
                "options": [{"text": "Start a new adventure", "next_scene": "start"}],
                "is_ending": True
            }
        else:
            options = generate_options(game_state, narrative_text)
            return {
                "narrative": narrative_text,
                "scene_description": scene_description,
                "options": options,
                "is_ending": False
            }

    except Exception as e:
        print(f"Error in narrative generation: {str(e)}")
        return {
            "narrative": "Something went wrong in your Marvel journey, but your mission continues...",
            "scene_description": "You're standing on the edge of something bigger — the fate of the multiverse is at stake.",
            "options": generate_options(game_state, "The hero faces the unknown."),
            "is_ending": False
        }


@app.route('/start_game', methods=['POST'])
def start_game():
    """Initialize a new Marvel superhero game session"""
    session_id = os.urandom(16).hex()
    game_state = GameState()
    sessions[session_id] = game_state

    # Get the initial scene from story framework
    scene_data = story_framework.get(game_state.current_scene)

    # Generate the opening scene
    result = generate_narrative(
        game_state,
        "begin your hero's journey",
        scene_data.get("ai_prompt", "Create an action-packed opening for a Marvel superhero origin.")
    )

    return jsonify({
        "session_id": session_id,
        "narrative": result["narrative"],
        "scene_description": result["scene_description"],
        "options": result["options"],
        "game_state": game_state.to_dict()
    })


@app.route('/make_choice', methods=['POST'])
def make_choice():
    """Process player choice and advance the story"""
    data = request.get_json()
    session_id = data.get("session_id")
    choice_index = data.get("choice_index", 0)
    custom_action = data.get("custom_action", "")
    
    if not session_id or session_id not in sessions:
        return jsonify({"error": "Invalid session"}), 400
    
    game_state = sessions[session_id]
    
    # Get current options
    current_options = data.get("current_options", [])
    if not current_options:
        return jsonify({"error": "No options provided"}), 400
    
    # Handle the choice
    if choice_index >= len(current_options):
        return jsonify({"error": "Invalid choice index"}), 400
    
    chosen_option = current_options[choice_index]
    chosen_text = chosen_option.get("text", "Unknown choice")
    next_scene = chosen_option.get("next_scene", "")
    
    # For custom actions (the "Other" option)
    if next_scene == "custom_action" and custom_action:
        chosen_text = custom_action
        # Generate a scene ID for the custom action
        next_scene = "scene_custom_" + str(len(game_state.visited_locations))
    
    # Update game state
    game_state.visited_locations.append(game_state.current_scene)
    game_state.current_scene = next_scene
    
    # Generate narrative based on choice
    ai_prompt = f"The player chose to {chosen_text}. Continue the adventure based on this choice, creating a detailed and atmospheric scene."
    
    result = generate_narrative(
        game_state,
        chosen_text,
        ai_prompt
    )
    
    # Check if this is an ending
    if result.get("is_ending", False):
        # Reset certain game state aspects while preserving session
        game_state.inventory = []
        game_state.visited_locations = []
        game_state.current_scene = "start"
    
    return jsonify({
        "narrative": result["narrative"],
        "scene_description": result["scene_description"],
        "options": result["options"],
        "game_state": game_state.to_dict(),
        "is_ending": result.get("is_ending", False)
    })

@app.route('/custom_action', methods=['POST'])
def custom_action():
    """Process a custom player action"""
    data = request.get_json()
    session_id = data.get("session_id")
    custom_action = data.get("custom_action", "")
    
    if not session_id or session_id not in sessions or not custom_action:
        return jsonify({"error": "Invalid session or missing custom action"}), 400
    
    game_state = sessions[session_id]
    
    # Update game state
    game_state.visited_locations.append(game_state.current_scene)
    game_state.current_scene = f"scene_custom_{len(game_state.visited_locations)}"
    
    # Generate narrative based on custom action
    ai_prompt = f"The player chose a custom action: '{custom_action}'. Create an engaging continuation of the story based on this unexpected action."
    
    result = generate_narrative(
        game_state,
        custom_action,
        ai_prompt
    )
    
    return jsonify({
        "narrative": result["narrative"],
        "scene_description": result["scene_description"],
        "options": result["options"],
        "game_state": game_state.to_dict(),
        "is_ending": result.get("is_ending", False)
    })

@app.route('/save_game', methods=['POST'])
def save_game():
    """Save the current game state"""
    data = request.get_json()
    session_id = data.get("session_id")
    
    if not session_id or session_id not in sessions:
        return jsonify({"error": "Invalid session"}), 400
    
    game_state = sessions[session_id]
    
    # In a real implementation, you would save this to a database
    # For demonstration, we'll just return the serialized state
    return jsonify({
        "session_id": session_id,
        "game_state": game_state.to_dict()
    })

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # handle form input or game logic
        user_input = request.form.get("user_input", "")
        prompt = f"{user_input}\nWhat happens next?"
        ai_response = generate_ai_content(prompt)
        return render_template("index.html", ai_output=ai_response)
    
    # Default GET request (first page load)
    return render_template("index1.html", ai_output="Welcome to The Crystal Seeker!")


@app.route('/load_game', methods=['POST'])
def load_game():
    """Load a saved game state"""
    data = request.get_json()
    session_id = data.get("session_id")
    game_state_data = data.get("game_state")
    
    if not session_id or not game_state_data:
        return jsonify({"error": "Invalid session or game state"}), 400
    
    # Create a new game state and populate it
    game_state = GameState()
    game_state.from_dict(game_state_data)
    sessions[session_id] = game_state
    
    # Generate options for the current state
    ai_prompt = "The player has returned to the game. Remind them of their current situation and provide options."
    
    result = generate_narrative(
        game_state,
        "continue the adventure",
        ai_prompt
    )
    
    return jsonify({
        "session_id": session_id,
        "narrative": result["narrative"],
        "scene_description": result["scene_description"],
        "options": result["options"],
        "game_state": game_state.to_dict()
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(debug=True)