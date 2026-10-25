import json
import os
import sys
import copy
from typing import Dict, Any, List

def get_base_dir() -> str:
    """Trả về thư mục chứa file .exe (khi đóng gói) hoặc thư mục gốc dự án."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_CONFIG: Dict[str, Any] = {
    "version": "2.0",
    "roll_button": {
        "x": 1000,
        "y": 600
    },
    "watch_regions": [
        {
            "id": "slot_area_1",
            "name": "Vùng kiểm tra đồ",
            "x": 400,
            "y": 300,
            "w": 400,
            "h": 250
        }
    ],
    "target_colors": [
        "purple",
        "red"
    ],
    "color_definitions": {
        "purple": {
            "name": "Tím (Purple / Epic)",
            "h_min": 125,
            "h_max": 160,
            "s_min": 60,
            "s_max": 255,
            "v_min": 60,
            "v_max": 255
        },
        "red": {
            "name": "Đỏ (Red / Mythic)",
            "h_min": 0,
            "h_max": 10,
            "s_min": 100,
            "s_max": 255,
            "v_min": 80,
            "v_max": 255,
            "h2_min": 170,
            "h2_max": 180
        },
        "gold": {
            "name": "Vàng (Gold / Legendary)",
            "h_min": 20,
            "h_max": 35,
            "s_min": 100,
            "s_max": 255,
            "v_min": 100,
            "v_max": 255
        },
        "blue": {
            "name": "Xanh dương (Blue / Rare)",
            "h_min": 95,
            "h_max": 125,
            "s_min": 80,
            "s_max": 255,
            "v_min": 70,
            "v_max": 255
        },
        "green": {
            "name": "Xanh lá (Green / Uncommon)",
            "h_min": 35,
            "h_max": 85,
            "s_min": 60,
            "s_max": 255,
            "v_min": 60,
            "v_max": 255
        }
    },
    "action_rules": {
        "red": "stop",
        "purple": "lock",
        "gold": "stop",
        "blue": "lock"
    },
    "match_threshold_percent": 1.0,
    "delay_between_rolls": 1.5,
    "delay_random_offset_ms": 100,
    "max_rolls": 100,
    "play_sound": True,
    "save_screenshot": True,
    "hotkeys": {
        "start_pause": "f6",
        "stop": "f7"
    }
}


class ConfigManager:
    """Manages loading, updating, and saving configuration settings."""

    def __init__(self, config_path: str = "config.json"):
        if not os.path.isabs(config_path):
            config_path = os.path.join(get_base_dir(), config_path)
        self.config_path = os.path.abspath(config_path)
        self.data: Dict[str, Any] = self.load()


    def load(self) -> Dict[str, Any]:
        """Loads configuration from JSON file or initializes with default values."""
        if not os.path.exists(self.config_path):
            self.data = copy.deepcopy(DEFAULT_CONFIG)
            self.save()
            return self.data

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                merged = copy.deepcopy(DEFAULT_CONFIG)
                merged.update(loaded)
                self.data = merged
                return self.data
        except Exception as e:
            print(f"[ConfigManager] Error reading config: {e}. Using defaults.")
            self.data = copy.deepcopy(DEFAULT_CONFIG)
            return self.data

    def save(self) -> bool:
        """Saves current configuration to file."""
        try:
            dir_name = os.path.dirname(self.config_path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[ConfigManager] Error saving config: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True):
        self.data[key] = value
        if auto_save:
            self.save()

    def get_roll_button(self) -> Dict[str, int]:
        return self.data.get("roll_button", {"x": 1000, "y": 600})

    def set_roll_button(self, x: int, y: int, auto_save: bool = True):
        self.data["roll_button"] = {"x": int(x), "y": int(y)}
        if auto_save:
            self.save()

    def get_watch_regions(self) -> List[Dict[str, Any]]:
        return self.data.get("watch_regions", [])

    def set_primary_region(self, x: int, y: int, w: int, h: int, auto_save: bool = True):
        regions = self.data.setdefault("watch_regions", [])
        if not regions:
            regions.append({
                "id": "slot_area_1",
                "name": "Vùng kiểm tra đồ",
                "x": int(x),
                "y": int(y),
                "w": int(w),
                "h": int(h)
            })
        else:
            regions[0]["x"] = int(x)
            regions[0]["y"] = int(y)
            regions[0]["w"] = int(w)
            regions[0]["h"] = int(h)
        if auto_save:
            self.save()

    def get_target_colors(self) -> List[str]:
        return self.data.get("target_colors", ["purple", "red"])

    def set_target_colors(self, colors: List[str], auto_save: bool = True):
        self.data["target_colors"] = colors
        if auto_save:
            self.save()
