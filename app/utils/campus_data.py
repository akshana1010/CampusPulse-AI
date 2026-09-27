"""
CampusPulse AI – SMVEC Campus Spatial & Building Data Reference
Provides structured polygon geometries, centroids, and department metadata
anchored around the SMVEC campus geographic center (11.91411 N, 79.63558 E).
"""

SMVEC_CENTER = {
    "lat": 11.91411,
    "lng": 79.63558,
    "zoom": 16,
    "name": "Sri Manakula Vinayagar Engineering College (SMVEC)",
    "address": "Madagadipet, Puducherry 605107, India"
}

SMVEC_CAMPUS_AREAS = [
    {
        "id": "smvec-admin-block",
        "code": "ADMIN",
        "name": "Main Administrative Block & Admissions",
        "category": "Administration",
        "description": "Principal Office, Dean Offices, Administrative Offices, Admissions & Examination Wing.",
        "center": [11.91480, 79.63558],
        "polygon": [
            [11.91510, 79.63520],
            [11.91510, 79.63595],
            [11.91450, 79.63595],
            [11.91450, 79.63520]
        ],
        "color": "#6366f1"
    },
    {
        "id": "smvec-central-library",
        "code": "LIB",
        "name": "Central Library & Digital Knowledge Centre",
        "category": "Academic",
        "description": "Central Book Bank, Digital Knowledge Centre, Reading Halls, Research & Periodicals Wing.",
        "center": [11.91411, 79.63558],
        "polygon": [
            [11.91435, 79.63525],
            [11.91435, 79.63590],
            [11.91385, 79.63590],
            [11.91385, 79.63525]
        ],
        "color": "#3b82f6"
    },
    {
        "id": "smvec-cse-it-block",
        "code": "CSE-IT",
        "name": "CSE, IT & AI-DS Academic Block",
        "category": "Engineering",
        "description": "Computer Science, Information Technology, AI & Data Science labs, Server Rooms and Smart Classrooms.",
        "center": [11.91440, 79.63665],
        "polygon": [
            [11.91475, 79.63615],
            [11.91475, 79.63715],
            [11.91405, 79.63715],
            [11.91405, 79.63615]
        ],
        "color": "#06b6d4"
    },
    {
        "id": "smvec-eee-ece-block",
        "code": "EEE-ECE",
        "name": "ECE & EEE Engineering Block",
        "category": "Engineering",
        "description": "Electronics & Communication, Electrical & Electronics labs, Microcontroller and Robotics Studios.",
        "center": [11.91350, 79.63665],
        "polygon": [
            [11.91385, 79.63615],
            [11.91385, 79.63715],
            [11.91315, 79.63715],
            [11.91315, 79.63615]
        ],
        "color": "#f59e0b"
    },
    {
        "id": "smvec-mech-civil-block",
        "code": "MECH-CIVIL",
        "name": "Mechanical & Civil Engineering Block",
        "category": "Engineering",
        "description": "Mechanical Design Studios, Civil Fluid Mechanics & Surveying labs, CAD/CAM Centre.",
        "center": [11.91320, 79.63558],
        "polygon": [
            [11.91360, 79.63520],
            [11.91360, 79.63595],
            [11.91280, 79.63595],
            [11.91280, 79.63520]
        ],
        "color": "#ea580c"
    },
    {
        "id": "smvec-science-humanities",
        "code": "S&H",
        "name": "Science & Humanities Block (Freshman Wing)",
        "category": "Academic",
        "description": "First-year lecture halls, Physics & Chemistry Laboratories, Mathematics Department and Language Labs.",
        "center": [11.91420, 79.63450],
        "polygon": [
            [11.91450, 79.63410],
            [11.91450, 79.63490],
            [11.91390, 79.63490],
            [11.91390, 79.63410]
        ],
        "color": "#10b981"
    },
    {
        "id": "smvec-auditorium",
        "code": "AUD",
        "name": "Main Auditorium & Convention Hall",
        "category": "Facilities",
        "description": "Sri Manakula Vinayagar Central Auditorium, Seminar Halls, Placement & Training Centre.",
        "center": [11.91490, 79.63450],
        "polygon": [
            [11.91520, 79.63410],
            [11.91520, 79.63490],
            [11.91460, 79.63490],
            [11.91460, 79.63410]
        ],
        "color": "#a855f7"
    },
    {
        "id": "smvec-canteen",
        "code": "CANTEEN",
        "name": "Central Food Court & Student Canteen",
        "category": "Amenities",
        "description": "Campus cafeteria, student dining hall, refreshment stalls and stationery depot.",
        "center": [11.91350, 79.63450],
        "polygon": [
            [11.91375, 79.63410],
            [11.91375, 79.63490],
            [11.91325, 79.63490],
            [11.91325, 79.63410]
        ],
        "color": "#84cc16"
    },
    {
        "id": "smvec-workshops-incubation",
        "code": "WORKSHOP",
        "name": "Central Workshops & Incubation Centre",
        "category": "Facilities",
        "description": "Foundry, Welding, Machine Shop, Carpentry, Technology Incubation & Startup Centre.",
        "center": [11.91250, 79.63560],
        "polygon": [
            [11.91275, 79.63510],
            [11.91275, 79.63610],
            [11.91225, 79.63610],
            [11.91225, 79.63510]
        ],
        "color": "#e11d48"
    },
    {
        "id": "smvec-boys-hostel",
        "code": "BH",
        "name": "Boys Hostel & Dining Complex",
        "category": "Residential",
        "description": "Men's Student Residential Blocks, Study Rooms and Hostel Mess.",
        "center": [11.91270, 79.63450],
        "polygon": [
            [11.91305, 79.63400],
            [11.91305, 79.63500],
            [11.91235, 79.63500],
            [11.91235, 79.63400]
        ],
        "color": "#4f46e5"
    },
    {
        "id": "smvec-girls-hostel",
        "code": "GH",
        "name": "Girls Hostel Complex",
        "category": "Residential",
        "description": "Women's Student Residential Wings, Safe Pathway, Study Lounge and Dining Wing.",
        "center": [11.91450, 79.63340],
        "polygon": [
            [11.91490, 79.63290],
            [11.91490, 79.63390],
            [11.91410, 79.63390],
            [11.91410, 79.63290]
        ],
        "color": "#ec4899"
    },
    {
        "id": "smvec-sports-ground",
        "code": "SPORTS",
        "name": "Main Sports Ground & Athletics Complex",
        "category": "Amenities",
        "description": "Cricket ground, Football field, Volleyball and Basketball courts, Gymnasium & Athletic tracks.",
        "center": [11.91250, 79.63680],
        "polygon": [
            [11.91295, 79.63630],
            [11.91295, 79.63740],
            [11.91200, 79.63740],
            [11.91200, 79.63630]
        ],
        "color": "#22c55e"
    },
    {
        "id": "smvec-main-gate",
        "code": "GATE",
        "name": "Main Campus Entrance & Security Gate",
        "category": "Security",
        "description": "Main Entrance Arch, 24/7 Security Cabin, Visitor Check-in Point (NH Road Access).",
        "center": [11.91550, 79.63558],
        "polygon": [
            [11.91570, 79.63520],
            [11.91570, 79.63595],
            [11.91530, 79.63595],
            [11.91530, 79.63520]
        ],
        "color": "#64748b"
    },
    {
        "id": "smvec-parking",
        "code": "PARKING",
        "name": "Vehicle Parking Arena",
        "category": "Facilities",
        "description": "Student Two-Wheeler and Staff Four-Wheeler designated sheltered parking bays.",
        "center": [11.91540, 79.63660],
        "polygon": [
            [11.91565, 79.63615],
            [11.91565, 79.63705],
            [11.91515, 79.63705],
            [11.91515, 79.63615]
        ],
        "color": "#0284c7"
    }
]

def get_building_by_id(building_id: str):
    """Retrieve building area object by ID."""
    for b in SMVEC_CAMPUS_AREAS:
        if b["id"] == building_id or b["code"].lower() == building_id.lower():
            return b
    return None

def get_building_by_name(name: str):
    """Retrieve building area object by name."""
    if not name:
        return None
    name_clean = name.strip().lower()
    for b in SMVEC_CAMPUS_AREAS:
        if b["name"].lower() == name_clean or b["id"].lower() == name_clean:
            return b
    # Partial match
    for b in SMVEC_CAMPUS_AREAS:
        if b["name"].lower() in name_clean or name_clean in b["name"].lower():
            return b
    return None
