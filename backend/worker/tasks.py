import json
import os
from uuid import UUID
from google import genai  # <-- Pustaka baru Google

from database import SessionLocal
import models

def process_trip(trip_id: str) -> None:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    db = SessionLocal()
    trip = None
    try:
        trip_uuid = UUID(trip_id)
        trip = db.query(models.Trip).filter(models.Trip.id == trip_uuid).first()
        if not trip:
            return

        destination_names = [
            f"{dest.name} (Likes: {dest.likes}, Dislikes: {dest.dislikes})"
            for dest in trip.destinations
        ]
        start_location = trip.start_location or "Titik Kumpul"

        ai_prompt = f"""
        Anda adalah Pakar Transportasi Publik & Pariwisata Jakarta.
        Tugas Anda menyusun rute perjalanan 1 hari yang efisien di Jakarta.

        DATA PERJALANAN:
        - Titik Kumpul (Awal): {start_location}
        - Wishlist Destinasi: {destination_names}

        ATURAN KETAT:
        1. Rute WAJIB dimulai dari "{start_location}". Coret destinasi di luar Jakarta.
        2. Di bagian "summary", sebutkan total perkiraan biaya (transportasi + tiket wisata) untuk trip ini.
        3. Di dalam array "ordered_route", tambahkan info harga tiket dan jam buka di sebelah nama tempat. (Contoh: "Moja Museum (Rp 135.000 | 11:00-19:30)").
        4. Di dalam array "transit_steps", sebutkan rute spesifik (Transjakarta/MRT/KRL) beserta biaya transportasinya. (Contoh: "Naik MRT ke Senayan (Rp 5.000), lalu jalan kaki").
        5. PRIORITASKAN memasukkan destinasi yang memiliki banyak "Likes" ke dalam rute. CORET destinasi yang memiliki lebih banyak "Dislikes" daripada "Likes".
        
        KEMBALIKAN HANYA JSON DENGAN FORMAT BERIKUT TANPA TEKS TAMBAHAN:
        {{
            "summary": "Total Estimasi Biaya: Rp 150.000. Rute ini...",
            "feasible_destinations": ["Destinasi 1"],
            "removed_destinations": [],
            "removal_reason": "",
            "ordered_route": ["{start_location}", "Nama Tempat (Harga | Jam)"],
            "transit_steps": ["Titik awal keberangkatan", "Naik TJ Koridor 1 (Rp 3.500)..."]
        }}
        """

        # Cara baru memanggil Gemini 1.5 Flash
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=ai_prompt,
        )

        # Bersihkan format response 
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:-3].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:-3].strip()

        # Konversi string JSON ke Python Dictionary
        ai_insight = json.loads(raw_text)

        # Tandai mana destinasi yang masuk akal (feasible) dan mana yang dicoret
        feasible_names = set(ai_insight.get("feasible_destinations", []))
        for dest in trip.destinations:
            dest.is_feasible = dest.name in feasible_names

        # Simpan hasil ke database
        trip.ai_insight = ai_insight
        trip.status = "completed"
        db.commit()
        
    except Exception as e:
        db.rollback()
        print(f"[Worker Error] Gagal memproses rute AI: {e}")
        if trip:
            try:
                trip.status = "failed"
                db.commit()
            except Exception:
                db.rollback()
        raise
    finally:
        db.close()