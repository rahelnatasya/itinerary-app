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
        Anda adalah Pakar Transportasi Publik & Perencana Perjalanan Jakarta.
          Tugas Anda menyusun rute 1 hari (maksimal 10-12 jam perjalanan & wisata) yang rasional dan efisien.

          DATA PERJALANAN:
          - Titik Kumpul (Awal): {start_location}
          - Wishlist Destinasi & Vote: {destination_names}
             *(Catatan: Format list berupa "Nama Destinasi (Likes: X, Dislikes: Y)")*

          ALGORITMA & ATURAN KETAT:
          1. PENYARINGAN AWAL: Coret destinasi di luar wilayah Jakarta atau yang memiliki "Dislikes" lebih banyak dari "Likes".
          2. PENENTUAN URUTAN (SANGAT PENTING):
              - Rute WAJIB dimulai dari Titik Kumpul: "{start_location}".
              - Destinasi PERTAMA yang dikunjungi WAJIB destinasi dengan jumlah "Likes" TERBANYAK.
              - Destinasi KEDUA dan seterusnya WAJIB dipilih berdasarkan JARAK TERDEKAT (geografis/waktu tempuh) dari destinasi sebelumnya, agar tidak membuang waktu bolak-balik di jalan.
          3. BATASAN WAKTU (FEASIBILITY CHECK):
              - Kalkulasi estimasi total waktu (waktu transit antar lokasi + durasi standar wisata di tiap tempat).
              - Jika total waktu untuk mengunjungi semua wishlist melebihi kapasitas 1 hari (lebih dari 12 jam), HENTIKAN penambahan destinasi.
              - Masukkan sisa destinasi yang tidak muat waktunya ke array "removed_destinations".
              - Di bagian "removal_reason", jelaskan dengan spesifik: "Waktu tidak cukup untuk mengunjungi semua destinasi dalam 1 hari, sehingga destinasi X dan Y dihapus."
          4. KONTEN RESPON:
              - "summary": Berikan kesimpulan apakah rencana awal mereka realistis. Sebutkan juga total estimasi biaya (transport + tiket).
              - "ordered_route": Tambahkan info harga tiket dan jam operasional. (Contoh: "Monas (Rp 15.000 | 08:00-16:00)").
              - "transit_steps": Berikan rute spesifik (Transjakarta/MRT) dan biaya antar titik lokasi.
        
          KEMBALIKAN HANYA JSON DENGAN FORMAT BERIKUT TANPA TEKS TAMBAHAN:
          {{
                "summary": "Kesimpulan kelayakan waktu... Total Estimasi Biaya: Rp 150.000...",
                "feasible_destinations": ["Destinasi 1", "Destinasi 2"],
                "removed_destinations": ["Destinasi Sisa 1", "Destinasi Sisa 2"],
                "removal_reason": "Waktu tidak cukup untuk dikunjungi semua dalam 1 hari...",
                "ordered_route": ["{start_location}", "Destinasi 1 (Harga | Jam)", "Destinasi 2 (Harga | Jam)"],
                "transit_steps": ["Dari start naik X ke Destinasi 1...", "Jalan kaki ke Destinasi 2..."]
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