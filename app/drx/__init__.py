"""
drx/ — DRX Integration Client

This module knows how to talk to DRX.
It is NOT DRX itself — it's just a client.

Like sarvam/ knows how to talk to Sarvam AI,
drx/ knows how to talk to the DRX backend.
"""

from app.drx.doctor_service import DRXDoctorService

__all__ = ["DRXDoctorService"]
