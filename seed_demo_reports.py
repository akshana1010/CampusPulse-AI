"""
Seed script to create 8 realistic sample college reports across different categories.
"""
from datetime import datetime, timezone, timedelta
from app import create_app, db
from app.models import User, Report, StatusHistory

def seed_reports():
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        if not user:
            user = User.query.first()
        admin = User.query.filter_by(role='admin').first()
        admin_id = admin.id if admin else user.id

        now = datetime.now(timezone.utc)

        sample_reports = [
            {
                "title": "[Demo] Broken Streetlight Near Girls Hostel Pathway",
                "description": "The main streetlight along the pathway connecting the Girls Hostel and the Dining Hall has been non-functional for 3 days. The area gets completely pitch dark after 7:30 PM, raising serious safety concerns for walking students.",
                "category": "Safety",
                "priority": "Critical",
                "status": "In Progress",
                "latitude": 11.9218,
                "longitude": 79.6375,
                "location_label": "Girls Hostel South Pathway",
                "ai_category": "Safety",
                "ai_summary": "Report highlights dark pathway near Girls Hostel due to non-functional streetlight creating safety hazard.",
                "ai_sentiment": "urgent",
                "ai_confidence": 0.94,
                "created_at": now - timedelta(days=2, hours=4),
                "note": "Estate office dispatched electrician team."
            },
            {
                "title": "[Demo] Frequent Power Fluctuations & Exposed Wire in Electrical Lab B",
                "description": "There is an open switchboard with exposed wires near workstation 4 in Electrical Engineering Lab B. Voltage fluctuations have caused equipment to trip during practical sessions.",
                "category": "Electricity",
                "priority": "High",
                "status": "Reported",
                "latitude": 11.9215,
                "longitude": 79.6390,
                "location_label": "EE Lab Block - Room 204",
                "ai_category": "Electricity",
                "ai_summary": "Exposed wiring and voltage drops in Electrical Lab B posing risk of short circuit.",
                "ai_sentiment": "negative",
                "ai_confidence": 0.91,
                "created_at": now - timedelta(days=1, hours=2),
                "note": None
            },
            {
                "title": "[Demo] Drinking Water Dispenser Leakage and Shortage on 2nd Floor",
                "description": "The water cooler on the second floor of the Main Academic Block is leaking heavily and not dispensing clean chilled water. Students have to walk down to ground floor between lectures.",
                "category": "Water",
                "priority": "Medium",
                "status": "In Progress",
                "latitude": 11.9210,
                "longitude": 79.6382,
                "location_label": "Main Academic Block 2nd Floor Corridor",
                "ai_category": "Water",
                "ai_summary": "Water cooler leaking and shortage on 2nd floor academic building.",
                "ai_sentiment": "negative",
                "ai_confidence": 0.88,
                "created_at": now - timedelta(days=3, hours=6),
                "note": "Plumber scheduled for filter replacement."
            },
            {
                "title": "[Demo] Campus Wi-Fi Signal Dropouts in Central Library Reading Hall",
                "description": "Wi-Fi access points 'Campus_Student_5G' in the 1st floor reading hall are constantly dropping connections and giving DNS failure errors, making research and digital study difficult.",
                "category": "Internet",
                "priority": "Medium",
                "status": "Reported",
                "latitude": 11.9220,
                "longitude": 79.6380,
                "location_label": "Central Library - Digital Study Section",
                "ai_category": "Internet",
                "ai_summary": "Wi-Fi connection instability and frequent drops in Central Library study area.",
                "ai_sentiment": "neutral",
                "ai_confidence": 0.89,
                "created_at": now - timedelta(hours=8),
                "note": None
            },
            {
                "title": "[Demo] Overflowing Waste Bins Behind Student Cafeteria",
                "description": "Trash bins behind the cafeteria building have not been cleared since yesterday afternoon. Food waste is spilling onto the walkway and attracting stray animals and pests.",
                "category": "Cleanliness",
                "priority": "High",
                "status": "Resolved",
                "latitude": 11.9205,
                "longitude": 79.6378,
                "location_label": "Cafeteria Courtyard",
                "ai_category": "Cleanliness",
                "ai_summary": "Waste overflow and hygiene issue behind campus cafeteria.",
                "ai_sentiment": "negative",
                "ai_confidence": 0.92,
                "created_at": now - timedelta(days=4),
                "resolved_at": now - timedelta(days=1),
                "note": "Cleaned and sanitized by sanitation crew."
            },
            {
                "title": "[Demo] Damaged Desk Benches and Broken Window Latches in Hall 102",
                "description": "Several wooden benches in Lecture Hall 102 are cracked and loose with exposed screws that snag clothes. Also the side window latches are broken, causing windows to bang during wind.",
                "category": "Infrastructure",
                "priority": "Medium",
                "status": "Reported",
                "latitude": 11.9212,
                "longitude": 79.6388,
                "location_label": "Lecture Complex Block A - Room 102",
                "ai_category": "Infrastructure",
                "ai_summary": "Damaged classroom furniture and broken window latches in Lecture Hall 102.",
                "ai_sentiment": "negative",
                "ai_confidence": 0.86,
                "created_at": now - timedelta(hours=14),
                "note": None
            },
            {
                "title": "[Demo] Campus Shuttle Delay and Overcrowding at Gate 2 Bus Stop",
                "description": "The morning 8:30 AM campus shuttle from South Gate to Academic Block is consistently arriving 25 minutes late and overcrowded, causing students to miss the start of early morning lectures.",
                "category": "Transport",
                "priority": "Low",
                "status": "In Progress",
                "latitude": 11.9225,
                "longitude": 79.6395,
                "location_label": "Campus Main Entrance - Gate 2 Shuttle Stop",
                "ai_category": "Transport",
                "ai_summary": "Shuttle bus timing delays and capacity issues during morning commute.",
                "ai_sentiment": "neutral",
                "ai_confidence": 0.85,
                "created_at": now - timedelta(days=1, hours=8),
                "note": "Transport supervisor coordinating with bus contractor."
            },
            {
                "title": "[Demo] Outdated Compilers & Broken Projector HDMI in CS Seminar Room",
                "description": "The main ceiling projector in Computer Science Seminar Hall displays distorted green tint and fails HDMI handshake with newer laptops. Also desktop systems require Python environment updates.",
                "category": "Academic",
                "priority": "Medium",
                "status": "Resolved",
                "latitude": 11.9214,
                "longitude": 79.6384,
                "location_label": "CS Department - 3rd Floor Seminar Hall",
                "ai_category": "Academic",
                "ai_summary": "Audio-visual projector malfunction and outdated lab environment in CS Seminar Hall.",
                "ai_sentiment": "neutral",
                "ai_confidence": 0.90,
                "created_at": now - timedelta(days=5),
                "resolved_at": now - timedelta(days=2),
                "note": "HDMI cable replaced and projector color calibration completed."
            }
        ]

        added_count = 0
        for data in sample_reports:
            existing = Report.query.filter_by(title=data["title"]).first()
            if not existing:
                note = data.pop("note", None)
                rep = Report()
                rep.user_id = user.id
                for k, v in data.items():
                    setattr(rep, k, v)
                db.session.add(rep)
                db.session.flush()

                # Add initial status history
                h1 = StatusHistory()
                h1.report_id = rep.id
                h1.old_status = None
                h1.new_status = "Reported"
                h1.changed_by = user.id
                h1.changed_at = rep.created_at
                h1.note = "Report submitted"
                db.session.add(h1)

                if rep.status != "Reported":
                    h2 = StatusHistory()
                    h2.report_id = rep.id
                    h2.old_status = "Reported"
                    h2.new_status = rep.status
                    h2.changed_by = admin_id
                    h2.changed_at = rep.created_at + timedelta(hours=2)
                    h2.note = note
                    db.session.add(h2)

                added_count += 1

        db.session.commit()
        print(f"Successfully added {added_count} sample reports for user: {user.email}")

if __name__ == "__main__":
    seed_reports()
