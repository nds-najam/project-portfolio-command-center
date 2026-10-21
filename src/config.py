"""Shared constants: reference lists, colours and the demo 'as of' date."""
from datetime import date

AS_OF = date(2026, 10, 1)  # fixed reporting date so demo numbers are reproducible

CLIENTS = ["Telecom Client A", "Telecom Client B", "Infrastructure Client A",
           "Enterprise Client A", "Government Client A"]
REGIONS = ["Riyadh", "Jeddah", "Dammam", "Khobar", "Mecca", "Medina", "Abha", "Tabuk"]
MANAGERS = ["Khalid Al-Harbi", "Faisal Al-Qahtani", "Omar Al-Ghamdi", "Nasser Al-Otaibi",
            "Saud Al-Dosari", "Majid Al-Shehri", "Turki Al-Zahrani", "Abdullah Al-Mutairi",
            "Yousef Al-Subaie", "Rakan Al-Anazi", "Hamad Al-Rashid", "Sultan Al-Malki",
            "Badr Al-Yami", "Ziad Al-Amri"]
PROJECT_TYPES = ["Fiber Deployment", "Network Upgrade", "Tower Deployment", "Civil Works",
                 "Infrastructure", "Enterprise Connectivity", "Maintenance"]
ISSUE_CATEGORIES = ["Material Delay", "Resource Shortage", "Permit Delay", "Client Dependency",
                    "Design Change", "Weather", "Vendor Delay", "Access Issue", "Quality Issue"]
SEVERITIES = ["Critical", "High", "Medium", "Low"]
RISK_LEVELS = ["Low", "Medium", "High"]
HEALTH_STATUSES = ["On Track", "At Risk", "Critical", "Completed"]
MILESTONE_STATUSES = ["Completed", "On Track", "At Risk", "Delayed"]

# Status palette (reserved meaning, vivid for visibility) + neutrals
COLORS = {
    "On Track": "#00C46A",
    "At Risk": "#FFAA00",
    "Critical": "#FF3B30",
    "Completed": "#8B5CF6",
    "Info": "#0A84FF",
    "Ink": "#1B2A41",
    "Muted": "#6B7A90",
    "Grid": "#E3E8EF",
}
SEVERITY_COLORS = {"Critical": "#FF3B30", "High": "#FF7A00", "Medium": "#FFC400", "Low": "#29B6F6"}
RISK_COLORS = {"Low": "#00C46A", "Medium": "#FFAA00", "High": "#FF3B30"}
MILESTONE_COLORS = {"Completed": "#8B5CF6", "On Track": "#00C46A", "At Risk": "#FFAA00", "Delayed": "#FF3B30"}
