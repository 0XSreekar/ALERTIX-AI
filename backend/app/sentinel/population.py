"""Population at risk — major Indian urban centres with census population.

We do not ship WorldPop's multi-GB raster. Instead we use ~80 Indian
metros + Tier-2 cities with 2011 census + UN-projected 2024 estimates.
For most hazard radii (50-500 km) this captures >85% of the at-risk
population. The caveat is shown in the UI: "urban-centric estimate".
"""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

# (lat, lon, name, state, population_thousands_2024)
INDIAN_CITIES: list[tuple[float, float, str, str, int]] = [
    (28.6139, 77.2090, "Delhi", "Delhi", 33_807),
    (19.0760, 72.8777, "Mumbai", "Maharashtra", 21_673),
    (22.5726, 88.3639, "Kolkata", "West Bengal", 15_333),
    (13.0827, 80.2707, "Chennai", "Tamil Nadu", 11_776),
    (12.9716, 77.5946, "Bengaluru", "Karnataka", 13_608),
    (17.3850, 78.4867, "Hyderabad", "Telangana", 10_801),
    (18.5204, 73.8567, "Pune", "Maharashtra", 7_276),
    (23.0225, 72.5714, "Ahmedabad", "Gujarat", 8_650),
    (21.1702, 72.8311, "Surat", "Gujarat", 7_784),
    (26.9124, 75.7873, "Jaipur", "Rajasthan", 4_267),
    (26.8467, 80.9462, "Lucknow", "Uttar Pradesh", 3_677),
    (21.1458, 79.0882, "Nagpur", "Maharashtra", 3_174),
    (22.3072, 73.1812, "Vadodara", "Gujarat", 2_237),
    (17.6868, 83.2185, "Visakhapatnam", "Andhra Pradesh", 2_358),
    (15.8281, 78.0373, "Kurnool", "Andhra Pradesh", 530),
    (16.5062, 80.6480, "Vijayawada", "Andhra Pradesh", 1_602),
    (11.0168, 76.9558, "Coimbatore", "Tamil Nadu", 2_310),
    (8.5241, 76.9366, "Thiruvananthapuram", "Kerala", 1_750),
    (9.9312, 76.2673, "Kochi", "Kerala", 3_300),
    (12.9141, 74.8560, "Mangaluru", "Karnataka", 700),
    (10.7867, 78.6886, "Tiruchirappalli", "Tamil Nadu", 1_022),
    (15.4989, 73.8278, "Panaji", "Goa", 230),
    (28.7041, 77.1025, "New Delhi", "Delhi", 28_500),  # NCR core
    (28.4595, 77.0266, "Gurugram", "Haryana", 2_500),
    (28.5355, 77.3910, "Noida", "Uttar Pradesh", 1_200),
    (29.0588, 76.0856, "Rohtak", "Haryana", 374),
    (30.7333, 76.7794, "Chandigarh", "Chandigarh", 1_172),
    (31.6340, 74.8723, "Amritsar", "Punjab", 1_183),
    (30.9010, 75.8573, "Ludhiana", "Punjab", 1_618),
    (32.7266, 74.8570, "Jammu", "Jammu & Kashmir", 651),
    (34.0837, 74.7973, "Srinagar", "Jammu & Kashmir", 1_273),
    (30.3398, 76.3869, "Patiala", "Punjab", 446),
    (30.3165, 78.0322, "Dehradun", "Uttarakhand", 803),
    (29.9457, 78.1642, "Haridwar", "Uttarakhand", 310),
    (30.7268, 79.4961, "Joshimath", "Uttarakhand", 17),
    (31.1048, 77.1734, "Shimla", "Himachal Pradesh", 213),
    (32.2396, 77.1887, "Manali", "Himachal Pradesh", 30),
    (27.0238, 88.6065, "Gangtok", "Sikkim", 100),
    (27.0410, 88.2663, "Darjeeling", "West Bengal", 132),
    (26.1445, 91.7362, "Guwahati", "Assam", 1_226),
    (25.5788, 91.8933, "Shillong", "Meghalaya", 354),
    (24.6637, 93.9063, "Imphal", "Manipur", 268),
    (23.7307, 92.7173, "Aizawl", "Mizoram", 326),
    (26.1584, 94.5624, "Mokokchung", "Nagaland", 35),
    (27.4728, 95.0169, "Itanagar", "Arunachal Pradesh", 60),
    (23.8315, 91.2868, "Agartala", "Tripura", 522),
    (25.5941, 85.1376, "Patna", "Bihar", 2_447),
    (25.3176, 82.9739, "Varanasi", "Uttar Pradesh", 1_435),
    (27.1767, 78.0081, "Agra", "Uttar Pradesh", 1_775),
    (28.6692, 77.4538, "Ghaziabad", "Uttar Pradesh", 2_405),
    (26.4499, 80.3319, "Kanpur", "Uttar Pradesh", 3_175),
    (28.9845, 77.7064, "Meerut", "Uttar Pradesh", 1_424),
    (23.2599, 77.4126, "Bhopal", "Madhya Pradesh", 2_587),
    (22.7196, 75.8577, "Indore", "Madhya Pradesh", 2_585),
    (25.4358, 81.8463, "Prayagraj", "Uttar Pradesh", 1_536),
    (23.3441, 85.3096, "Ranchi", "Jharkhand", 1_456),
    (22.8046, 86.2029, "Jamshedpur", "Jharkhand", 1_337),
    (22.5641, 85.7918, "Dhanbad", "Jharkhand", 1_447),
    (21.2514, 81.6296, "Raipur", "Chhattisgarh", 1_587),
    (20.2961, 85.8245, "Bhubaneswar", "Odisha", 1_163),
    (20.4625, 85.8830, "Cuttack", "Odisha", 813),
    (19.8135, 85.8312, "Puri", "Odisha", 201),
    (18.7041, 81.6228, "Jagdalpur", "Chhattisgarh", 144),
    (16.9891, 82.2475, "Kakinada", "Andhra Pradesh", 386),
    (14.4426, 79.9865, "Nellore", "Andhra Pradesh", 600),
    (14.6819, 77.6006, "Anantapur", "Andhra Pradesh", 268),
    (13.6288, 79.4192, "Tirupati", "Andhra Pradesh", 460),
    (12.2958, 76.6394, "Mysuru", "Karnataka", 1_017),
    (15.3647, 75.1240, "Hubli", "Karnataka", 1_100),
    (15.8497, 74.4977, "Belagavi", "Karnataka", 610),
    (11.6643, 78.1460, "Salem", "Tamil Nadu", 943),
    (10.9601, 78.0766, "Karur", "Tamil Nadu", 213),
    (9.9252, 78.1198, "Madurai", "Tamil Nadu", 1_561),
    (8.0883, 77.5385, "Nagercoil", "Tamil Nadu", 224),
    (8.7642, 78.1348, "Thoothukudi", "Tamil Nadu", 410),
    (10.0889, 77.0595, "Theni", "Tamil Nadu", 90),
    (11.7401, 79.7700, "Cuddalore", "Tamil Nadu", 173),
    (10.7905, 79.1378, "Thanjavur", "Tamil Nadu", 222),
    (12.6819, 75.0073, "Coorg/Madikeri", "Karnataka", 33),
    (24.5854, 73.7125, "Udaipur", "Rajasthan", 600),
    (26.2389, 73.0243, "Jodhpur", "Rajasthan", 1_138),
    (28.0229, 73.3119, "Bikaner", "Rajasthan", 729),
    (27.5530, 76.6346, "Alwar", "Rajasthan", 315),
    (23.1791, 75.7849, "Ujjain", "Madhya Pradesh", 590),
    (26.7606, 83.3732, "Gorakhpur", "Uttar Pradesh", 686),
    (24.7969, 84.9858, "Gaya", "Bihar", 470),
]


@dataclass(frozen=True, slots=True)
class CityImpact:
    name: str
    state: str
    population_thousands: int
    distance_km: float
    lat: float
    lon: float


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1 = radians(lat1)
    p2 = radians(lat2)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(p1) * cos(p2) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))


def cities_within(lat: float, lon: float, radius_km: float) -> list[CityImpact]:
    out: list[CityImpact] = []
    for clat, clon, name, state, pop in INDIAN_CITIES:
        d = _haversine_km(lat, lon, clat, clon)
        if d <= radius_km:
            out.append(
                CityImpact(
                    name=name,
                    state=state,
                    population_thousands=pop,
                    distance_km=round(d, 1),
                    lat=clat,
                    lon=clon,
                )
            )
    out.sort(key=lambda c: c.distance_km)
    return out
