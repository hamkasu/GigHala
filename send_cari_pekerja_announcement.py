"""
Script to send announcement email informing users that clients can now
search for registered workers with skills directly from the landing page,
and urging workers to update their profiles.

Usage:
  python send_cari_pekerja_announcement.py test <email@example.com>
  python send_cari_pekerja_announcement.py all
"""

import os
import sys
from flask import render_template

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, NotificationPreference
from email_service import EmailService

SUBJECT = "🔍 Klien Kini Boleh Cari Anda Terus — Kemaskini Profil Anda Sekarang!"
TEMPLATE = 'email_cari_pekerja_announcement.html'


def send_announcement(test_mode=True, test_email=None):
    with app.app_context():
        print(f"\n{'='*70}")
        print("GigHala — Penghantaran Emel Pengumuman: Cari Pekerja")
        print(f"{'='*70}\n")

        email_service = EmailService()
        base_url = os.getenv('BASE_URL', 'https://gighala.my')

        if test_mode:
            if not test_email:
                print("❌ Ralat: test_email diperlukan dalam mod ujian")
                return
            print(f"🧪 MOD UJIAN — Menghantar ke: {test_email}\n")
            users_to_email = [{
                'email': test_email,
                'full_name': 'Pengguna Ujian',
                'username': 'testuser',
            }]
        else:
            print("📊 Mendapatkan senarai pengguna dari pangkalan data...\n")

            users_query = db.session.query(User).outerjoin(
                NotificationPreference,
                User.id == NotificationPreference.user_id
            ).filter(
                User.email.isnot(None)
            )

            users_to_email = []
            for user in users_query.all():
                pref = db.session.query(NotificationPreference).filter_by(
                    user_id=user.id
                ).first()
                if not pref or pref.email_new_gig:
                    users_to_email.append({
                        'email': user.email,
                        'full_name': user.full_name,
                        'username': user.username,
                    })

            print(f"✅ Dijumpai {len(users_to_email)} pengguna\n")
            response = input(f"⚠️  Hantar kepada {len(users_to_email)} pengguna? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Dibatalkan")
                return

        successful, failed, failed_list = 0, 0, []
        total = len(users_to_email)

        for idx, user_data in enumerate(users_to_email, 1):
            try:
                name = user_data['full_name'] or user_data['username'] or 'Pengguna'
                email = user_data['email']

                print(f"📧 Menghantar {idx}/{total} ke {email}...")

                with app.test_request_context():
                    html_content = render_template(
                        TEMPLATE,
                        user_name=name,
                        base_url=base_url
                    )

                success, message, status_code, details = email_service.send_single_email(
                    to_email=email,
                    to_name=name,
                    subject=SUBJECT,
                    html_content=html_content
                )

                if success:
                    successful += 1
                    print(f"   ✓ Berjaya\n")
                else:
                    failed += 1
                    failed_list.append(email)
                    print(f"   ✗ Gagal: {message}\n")

                if not test_mode and idx % 10 == 0:
                    import time
                    time.sleep(1)

            except Exception as e:
                failed += 1
                failed_list.append(user_data['email'])
                print(f"   ✗ Ralat: {str(e)}\n")

        print(f"\n{'='*70}")
        print("RINGKASAN")
        print(f"{'='*70}")
        print(f"✅ Berjaya : {successful}")
        print(f"❌ Gagal   : {failed}")
        print(f"📊 Jumlah  : {total}")
        if failed_list:
            print("\nGagal dihantar kepada:")
            for e in failed_list[:10]:
                print(f"  - {e}")
            if len(failed_list) > 10:
                print(f"  ... dan {len(failed_list) - 10} lagi")
        print(f"\n{'='*70}\n")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            test_email = sys.argv[2] if len(sys.argv) > 2 else None
            if not test_email:
                print("Penggunaan: python send_cari_pekerja_announcement.py test <email>")
                sys.exit(1)
            send_announcement(test_mode=True, test_email=test_email)

        elif sys.argv[1] == 'all':
            print("\n⚠️  AMARAN: Ini akan menghantar emel kepada SEMUA pengguna!")
            confirm = input("Taip 'HANTAR SEMUA' untuk mengesahkan: ").strip()
            if confirm == 'HANTAR SEMUA':
                send_announcement(test_mode=False)
            else:
                print("❌ Dibatalkan")
        else:
            print("Penggunaan:")
            print("  python send_cari_pekerja_announcement.py test <email>")
            print("  python send_cari_pekerja_announcement.py all")
    else:
        while True:
            print("\nPilihan:")
            print("1. Hantar emel ujian")
            print("2. Hantar kepada semua pengguna (PRODUKSI)")
            print("3. Keluar")
            choice = input("\nPilih (1-3): ").strip()
            if choice == '1':
                email = input("Masukkan alamat emel ujian: ").strip()
                send_announcement(test_mode=True, test_email=email)
            elif choice == '2':
                send_announcement(test_mode=False)
            elif choice == '3':
                print("Selamat tinggal!")
                break
            else:
                print("❌ Pilihan tidak sah")
            if choice in ['1', '2']:
                input("\nTekan Enter untuk teruskan...")
