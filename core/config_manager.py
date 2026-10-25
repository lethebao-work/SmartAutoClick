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

def get_data_dir() -> str:
    """Trả về thư mục ghi dữ liệu người dùng (screenshots, logs, profiles, config).
    Nếu thư mục ứng dụng có quyền ghi, dùng luôn thư mục ứng dụng (portable mode).
    Nếu không (ví dụ cài đặt trong C:\\Program Files\\), fallback sang %APPDATA%/SmartAutoClick.
    """
    base = get_base_dir()
    test_file = os.path.join(base, ".write_test")
    try:
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return base
    except (OSError, PermissionError):
        appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
        data_dir = os.path.join(appdata, "SmartAutoClick")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

DEFAULT_COLOR_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "red": {
        "name": "Đỏ (Red / Mythic)",
        "h_min": 0,
        "h_max": 10,
        "s_min": 100,
        "s_max": 255,
        "v_min": 80,
        "v_max": 255,
        "h2_min": 170,
        "h2_max": 179
    },
    "gold": {
        "name": "Vàng (Gold / Legendary)",
        "h_min": 18,
        "h_max": 35,
        "s_min": 100,
        "s_max": 255,
        "v_min": 100,
        "v_max": 255
    },
    "purple": {
        "name": "Tím (Purple / Epic)",
        "h_min": 125,
        "h_max": 160,
        "s_min": 60,
        "s_max": 255,
        "v_min": 60,
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
}

def validate_color_definition(rule: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures HSV ranges are valid within OpenCV bounds [0..179] for H and [0..255] for S, V."""
    validated = dict(rule)
    validated["h_min"] = max(0, min(179, int(rule.get("h_min", 0))))
    validated["h_max"] = max(0, min(179, int(rule.get("h_max", 179))))
    validated["s_min"] = max(0, min(255, int(rule.get("s_min", 0))))
    validated["s_max"] = max(0, min(255, int(rule.get("s_max", 255))))
    validated["v_min"] = max(0, min(255, int(rule.get("v_min", 0))))
    validated["v_max"] = max(0, min(255, int(rule.get("v_max", 255))))
    if "h2_min" in rule and "h2_max" in rule:
        validated["h2_min"] = max(0, min(179, int(rule["h2_min"])))
        validated["h2_max"] = max(0, min(179, int(rule["h2_max"])))
    return validated

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
    "color_definitions": copy.deepcopy(DEFAULT_COLOR_DEFINITIONS),
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

    # ── Chụp màn hình ──
    # "auto" = DXGI (nhanh, hợp windowed/borderless) -> mss -> PIL. Có thể ép "dxgi" | "mss" | "pil".
    "capture_backend": "auto",

    # ── Đồng bộ theo khung hình sau mỗi click (thay cho delay cố định) ──
    "use_animation_detection": True,
    "anim_max_wait": 6.0,              # tối đa chờ ổn định (giây)
    "anim_first_change_timeout": 1.5,  # tối đa chờ game PHẢN HỒI sau click (giây)
    "anim_stable_ms": 250,             # phải tĩnh liên tục bấy nhiêu ms mới coi là xong
    "anim_post_delay": 0.1,            # nghỉ thêm sau khi ổn định (giây)
    "on_settle_failure": "stop",       # "stop" (an toàn) | "scan" (quét luôn, hành vi cũ)
    "settle_require_all": True,        # mọi slot đều phải đổi so với trước click
    "settle_pixel_delta": 15,
    "settle_change_start_pct": 0.5,
    "settle_stable_pct": 0.5,
    "settle_poll_ms": 10,

    # ── Xác nhận kết quả ──
    "confirm_frames": 2,               # số khung liên tiếp phải đồng thuận (1 = tắt)
    "confirm_gap_ms": 30,
    "uncertain_policy": "stop",        # màu đáng ngờ (>=40% ngưỡng): "stop" | "ignore"

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
        """Saves current configuration to file atomically via temp file."""
        try:
            dir_name = os.path.dirname(self.config_path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)
            tmp_path = f"{self.config_path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.config_path)
            return True
        except Exception as e:
            print(f"[ConfigManager] Error saving config: {e}")
            if os.path.exists(f"{self.config_path}.tmp"):
                try:
                    os.remove(f"{self.config_path}.tmp")
                except Exception:
                    pass
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

    def get_profiles_dir(self) -> str:
        pdir = os.path.join(get_data_dir(), "profiles")
        os.makedirs(pdir, exist_ok=True)
        return pdir

    def list_profiles(self) -> List[str]:
        """Returns all available profile names from profiles/ dir and internal dict."""
        names = set()
        pdir = self.get_profiles_dir()
        if os.path.exists(pdir):
            for fname in os.listdir(pdir):
                if fname.endswith(".json"):
                    names.add(fname[:-5])
        for k in self.data.get("profiles", {}).keys():
            names.add(k)
        if not names:
            names.add("default")
        return sorted(list(names))

    def save_profile(self, name: str, profile_data: Any = None) -> bool:
        """Saves full profile settings to profiles/<name>.json atomically and updates internal data."""
        if profile_data is None:
            # Capture full current configuration except meta profiles dictionary
            profile_data = {
                k: copy.deepcopy(v) for k, v in self.data.items()
                if k not in ("profiles", "active_profile")
            }
        profile_data["name"] = name

        # Save to profiles/<name>.json atomically
        pdir = self.get_profiles_dir()
        filepath = os.path.join(pdir, f"{name}.json")
        tmp_filepath = f"{filepath}.tmp"
        try:
            with open(tmp_filepath, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_filepath, filepath)
        except Exception as e:
            print(f"[ConfigManager] Error saving profile file {filepath}: {e}")
            if os.path.exists(tmp_filepath):
                try:
                    os.remove(tmp_filepath)
                except Exception:
                    pass
            return False

        # Also store in self.data["profiles"] for backward compatibility
        if "profiles" not in self.data:
            self.data["profiles"] = {}
        self.data["profiles"][name] = profile_data
        self.data["active_profile"] = name
        self.save()
        return True

    def load_profile(self, name: str) -> Any:
        """Loads full profile settings from profiles/<name>.json or internal dict, applying them to active config."""
        pdir = self.get_profiles_dir()
        filepath = os.path.join(pdir, f"{name}.json")
        loaded_data = None
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
            except Exception as e:
                print(f"[ConfigManager] Error reading profile {filepath}: {e}")

        if not loaded_data:
            loaded_data = self.data.get("profiles", {}).get(name)

        if loaded_data:
            # Apply all profile settings into self.data
            for k, v in loaded_data.items():
                if k not in ("profiles", "active_profile"):
                    self.data[k] = copy.deepcopy(v)
            self.data["active_profile"] = name
            self.save()
            return loaded_data
        return None

    def delete_profile(self, name: str) -> bool:
        """Deletes profile file and removes it from config."""
        pdir = self.get_profiles_dir()
        filepath = os.path.join(pdir, f"{name}.json")
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"[ConfigManager] Error deleting profile {filepath}: {e}")
        if "profiles" in self.data and name in self.data["profiles"]:
            del self.data["profiles"][name]
        if self.data.get("active_profile") == name:
            self.data["active_profile"] = "default"
        self.save()
        return True
