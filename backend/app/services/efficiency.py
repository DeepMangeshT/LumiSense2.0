"""LumiSense Efficiency Score Calculator.
Academic analytical metric (0-100) reflecting observed lighting behavior and room occupancy.

DISCLAIMER:
This is a project-defined analytical score and should not be interpreted as a
certified energy-efficiency standard or direct kWh measurement.
"""
from typing import Dict, Any, List, Optional
from app.database import get_readings_history, get_anomalies

def calculate_efficiency_score(source: Optional[str] = None) -> Dict[str, Any]:
    """Computes the project-defined LumiSense Efficiency Score based on the last 50 readings.
    Baseline is 100.
    Deductions are applied for:
    - Wastage pattern: High light (> 400) when unoccupied (motion == 0).
    - Unnecessary daytime over-illumination.
    - Active anomaly records.
    """
    recent_readings = get_readings_history(limit=50, source=source)
    if not recent_readings:
        return {
            "score": 85,
            "rating": "Optimal (Default)",
            "factors": {
                "unoccupied_light_penalty": 0,
                "anomaly_penalty": 0,
                "occupancy_rate_percent": 0.0,
                "readings_analyzed": 0
            },
            "disclaimer": (
                "This is a project-defined analytical score and should not be interpreted "
                "as a certified energy-efficiency rating."
            )
        }

    penalty_points = 0.0
    unoccupied_high_light_count = 0
    occupied_count = 0

    for r in recent_readings:
        light = r.get("light_smoothed") or r.get("light_raw", 0)
        motion = r.get("motion", 0)

        if motion == 1:
            occupied_count += 1
        else:
            # Unoccupied
            if light > 500:
                # Heavy light when nobody is in room -> strong indicator of unnecessary usage
                unoccupied_high_light_count += 1
                penalty_points += 1.5
            elif light > 300:
                unoccupied_high_light_count += 1
                penalty_points += 0.7

    # Check recent anomalies (last 15 minutes)
    anomalies = get_anomalies(limit=10)
    recent_anomaly_count = len(anomalies)
    anomaly_penalty = min(20.0, recent_anomaly_count * 3.0)
    penalty_points += anomaly_penalty

    # Compute final score
    score = int(max(10, min(100, round(100.0 - penalty_points))))

    if score >= 85:
        rating = "Excellent"
    elif score >= 70:
        rating = "Good"
    elif score >= 50:
        rating = "Fair"
    else:
        rating = "Inefficient"

    occupancy_rate = round((occupied_count / len(recent_readings)) * 100, 1)

    return {
        "score": score,
        "rating": rating,
        "factors": {
            "unoccupied_high_light_instances": unoccupied_high_light_count,
            "unoccupied_light_penalty": round(penalty_points - anomaly_penalty, 1),
            "anomaly_penalty": round(anomaly_penalty, 1),
            "occupancy_rate_percent": occupancy_rate,
            "readings_analyzed": len(recent_readings)
        },
        "disclaimer": (
            "This is a project-defined analytical score and should not be interpreted "
            "as a certified energy-efficiency rating."
        )
    }
