import json
import os
import re
import sys

def enrich_data(items):
    tech_keywords = [
        ("PyTorch", r"\bpytorch\b"),
        ("TensorFlow", r"\btensorflow\b"),
        ("OpenCV", r"\bopencv\b"),
        ("AI / ML", r"\b(ai|ml|machine learning|deep learning|artificial intelligence)\b"),
        ("NLP / LLM", r"\b(nlp|natural language|llm|large language model)\b"),
        ("Computer Vision", r"\b(computer vision|image processing|object detection)\b"),
        ("IoT / Sensors", r"\b(iot|internet of things|sensors?|sensor node)\b"),
        ("LoRaWAN", r"\blorawan\b"),
        ("Raspberry Pi", r"\braspberry pi\b"),
        ("STM32 / MCU", r"\b(stm32|microcontroller|mcu|arduino|esp32)\b"),
        ("Embedded C", r"\b(embedded|c\+\+|firmware)\b"),
        ("Blockchain", r"\b(blockchain|smart contracts?|web3|ethereum)\b"),
        ("GIS / Geospatial", r"\b(gis|geospatial|satellite|remote sensing|mapping)\b"),
        ("React / Web", r"\b(react|angular|vue|web application|frontend|portal)\b"),
        ("Mobile App", r"\b(mobile app|android|flutter|react native|ios)\b"),
        ("Cloud / API", r"\b(cloud|rest api|apis|microservices)\b"),
        ("Cybersecurity", r"\b(cybersecurity|cryptograph|security|encryption)\b"),
        ("Robotics / Drones", r"\b(robotics?|drones?|uav|autonomous)\b"),
    ]

    for item in items:
        subs = item.get("total_submissions", 0)
        win_odds = min(75.0, max(1.0, round(50.0 / (subs + 1), 1)))
        item["win_odds"] = win_odds

        if subs >= 25:
            item["comp_tier"] = "Fierce"
            item["comp_label"] = "Ultra High Competition"
            item["comp_color"] = "rose"
        elif subs >= 10:
            item["comp_tier"] = "Moderate"
            item["comp_label"] = "Moderate Contest"
            item["comp_color"] = "amber"
        else:
            item["comp_tier"] = "Hidden Gem"
            item["comp_label"] = "High Win Odds"
            item["comp_color"] = "emerald"

        search_text = (item.get("title", "") + " " + item.get("description", "")).lower()
        matched_tags = []
        for tag_name, pattern in tech_keywords:
            if re.search(pattern, search_text):
                matched_tags.append(tag_name)
                if len(matched_tags) >= 3:
                    break

        if not matched_tags:
            theme = item.get("theme", "")
            cat = item.get("category", "")
            if "Blockchain" in theme:
                matched_tags = ["Blockchain", "Security"]
            elif "Automation" in theme:
                matched_tags = ["Automation", "Cloud"]
            elif "Disaster" in theme:
                matched_tags = ["GIS", "Predictive Analytics"]
            elif "MedTech" in theme:
                matched_tags = ["Biomedical", "Data Analytics"]
            elif cat == "Hardware":
                matched_tags = ["Embedded Systems", "Sensors"]
            else:
                matched_tags = ["Full Stack", "System Architecture"]

        item["tech_stack"] = matched_tags

    return items

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def update_index_html(json_path=None, html_path=None):
    if json_path is None:
        json_path = os.path.join(ROOT_DIR, "data", "sih_ps_ranked.json")
    if html_path is None:
        html_path = os.path.join(ROOT_DIR, "index.html")

    if not os.path.exists(json_path):
        print(f"Error: {json_path} does not exist.")
        sys.exit(1)

    if not os.path.exists(html_path):
        print(f"Error: {html_path} does not exist.")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data = enrich_data(data)
    json_str = json.dumps(data, ensure_ascii=False)

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    import datetime
    # Format timestamp in IST (UTC+5:30)
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
    timestamp_str = ist_now.strftime("%d %b %Y, %I:%M %p IST")

    # Update HTML header timestamp span
    html_content = re.sub(
        r'(<span id="lastUpdatedTimestamp"[^>]*>)[^<]*(</span>)',
        rf'\g<1>{timestamp_str}\g<2>',
        html_content
    )

    # Robust replacement using exact delimiters
    if "const LAST_UPDATED = " in html_content:
        start_marker = "const LAST_UPDATED = "
    else:
        start_marker = "const DATA = "
    end_marker = "let state = {"
    start_idx = html_content.find(start_marker)
    end_idx = html_content.find(end_marker)

    replacement_block = f'const LAST_UPDATED = "{timestamp_str}";\n        const DATA = {json_str};\n\n        '

    if start_idx != -1 and end_idx != -1:
        html_content = html_content[:start_idx] + replacement_block + html_content[end_idx:]
    else:
        pattern = r"const DATA\s*=\s*\[[\s\S]*?\];"
        if re.search(pattern, html_content):
            html_content = re.sub(pattern, f"const DATA = {json_str};", html_content, count=1)
        elif "__DATA_PLACEHOLDER__" in html_content:
            html_content = html_content.replace("__DATA_PLACEHOLDER__", json_str)
        else:
            print("Error: Could not locate data injection target in index.html.")
            sys.exit(1)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Successfully updated {html_path} with {len(data)} problem statements from {json_path}.")

if __name__ == "__main__":
    update_index_html()

