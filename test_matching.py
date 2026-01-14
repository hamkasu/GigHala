"""
Test script for the AI-powered worker-gig matching system
Run this script to test the matching algorithm without waiting for scheduled jobs
"""

import os
import sys
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Gig, WorkerSpecialization, calculate_distance
from gig_matching_service import GigMatchingService


def test_single_worker_matching(user_id, hours_back=24):
    """
    Test matching for a specific worker

    Args:
        user_id: ID of the worker to test
        hours_back: How many hours back to look for gigs
    """
    with app.app_context():
        print(f"\n{'='*80}")
        print(f"Testing Worker-Gig Matching")
        print(f"{'='*80}\n")

        # Get the user
        user = db.session.query(User).get(user_id)
        if not user:
            print(f"❌ User with ID {user_id} not found")
            return

        print(f"👤 Worker: {user.full_name or user.username}")
        print(f"📧 Email: {user.email}")
        print(f"📍 Location: {user.location or 'Not set'}")

        # Get worker skills
        matching_service = GigMatchingService(
            db=db,
            User=User,
            Gig=Gig,
            WorkerSpecialization=WorkerSpecialization,
            calculate_distance=calculate_distance
        )

        worker_skills = matching_service.get_worker_skills(user)
        print(f"🎯 Skills: {', '.join(worker_skills) if worker_skills else 'None'}")

        # Get specializations
        specializations = WorkerSpecialization.query.filter_by(user_id=user.id).all()
        if specializations:
            print(f"⭐ Specializations:")
            for spec in specializations:
                from app import Category
                category = Category.query.get(spec.category_id)
                spec_skills = spec.skills if spec.skills else []
                print(f"   - {category.name if category else 'Unknown'}: {', '.join(spec_skills) if spec_skills else 'N/A'}")
        else:
            print(f"⭐ Specializations: None")

        print(f"\n{'='*80}")
        print(f"Finding matching gigs from the last {hours_back} hours...")
        print(f"{'='*80}\n")

        # Find matching gigs
        matches = matching_service.find_matching_gigs_for_worker(
            user,
            hours_back=hours_back,
            min_score=0.2  # Lower threshold for testing
        )

        if not matches:
            print(f"❌ No matching gigs found")

            # Show available gigs for debugging
            time_threshold = datetime.utcnow() - timedelta(hours=hours_back)
            total_gigs = Gig.query.filter(
                Gig.status == 'open',
                Gig.created_at >= time_threshold
            ).count()
            print(f"ℹ️  Total open gigs in the last {hours_back} hours: {total_gigs}")
            return

        print(f"✅ Found {len(matches)} matching gig(s):\n")

        for idx, match in enumerate(matches, 1):
            gig = match['gig']
            breakdown = match['breakdown']

            print(f"🎯 Match #{idx} - {match['match_percentage']}% Match")
            print(f"   Title: {gig.title}")
            print(f"   Code: {gig.gig_code}")
            print(f"   Category: {gig.category}")
            print(f"   Location: {gig.location or 'Not specified'} {'🌐 (Remote)' if gig.is_remote else ''}")

            if gig.budget_min and gig.budget_max:
                print(f"   Budget: RM {gig.budget_min:,.2f} - RM {gig.budget_max:,.2f}")

            print(f"\n   📊 Score Breakdown:")
            print(f"      Overall: {breakdown['overall_score']:.2%}")
            print(f"      Skills: {breakdown['skill_score']:.2%}")
            print(f"      Category: {breakdown['category_score']:.2%}")
            print(f"      Location: {breakdown['location_score']:.2%}")
            print(f"      Budget: {breakdown['budget_score']:.2%}")
            print(f"      Freshness: {breakdown['freshness_score']:.2%}")

            if breakdown['matched_skills']:
                print(f"\n   ✓ Matched Skills: {', '.join(breakdown['matched_skills'])}")

            print()


def test_all_workers_matching(hours_back=24, limit=5):
    """
    Test matching for all workers

    Args:
        hours_back: How many hours back to look for gigs
        limit: Limit number of workers to show
    """
    with app.app_context():
        print(f"\n{'='*80}")
        print(f"Testing Matching for All Workers")
        print(f"{'='*80}\n")

        matching_service = GigMatchingService(
            db=db,
            User=User,
            Gig=Gig,
            WorkerSpecialization=WorkerSpecialization,
            calculate_distance=calculate_distance
        )

        # Get all worker matches
        worker_matches = matching_service.get_all_worker_matches(
            hours_back=hours_back,
            min_score=0.2  # Lower threshold for testing
        )

        print(f"✅ Found matches for {len(worker_matches)} worker(s)\n")

        if not worker_matches:
            print(f"❌ No workers have matching gigs")
            return

        # Show top N workers
        shown = 0
        for user_id, matches in list(worker_matches.items())[:limit]:
            user = db.session.query(User).get(user_id)
            if not user:
                continue

            shown += 1
            print(f"👤 {user.full_name or user.username} ({user.email})")
            print(f"   Found {len(matches)} matching gig(s)")
            print(f"   Top match: {matches[0]['gig'].title} ({matches[0]['match_percentage']}% match)")
            print()

        if len(worker_matches) > limit:
            print(f"... and {len(worker_matches) - shown} more worker(s) with matches")


def test_gig_matching(gig_id):
    """
    Test finding workers for a specific gig

    Args:
        gig_id: ID of the gig to test
    """
    with app.app_context():
        print(f"\n{'='*80}")
        print(f"Testing Finding Workers for a Gig")
        print(f"{'='*80}\n")

        # Get the gig
        gig = db.session.query(Gig).get(gig_id)
        if not gig:
            print(f"❌ Gig with ID {gig_id} not found")
            return

        print(f"💼 Gig: {gig.title}")
        print(f"🏷️  Code: {gig.gig_code}")
        print(f"📂 Category: {gig.category}")
        print(f"📍 Location: {gig.location or 'Not specified'} {'🌐 (Remote)' if gig.is_remote else ''}")

        matching_service = GigMatchingService(
            db=db,
            User=User,
            Gig=Gig,
            WorkerSpecialization=WorkerSpecialization,
            calculate_distance=calculate_distance
        )

        # Get required skills
        gig_skills = matching_service.get_gig_required_skills(gig)
        print(f"🎯 Required Skills: {', '.join(gig_skills) if gig_skills else 'None'}")

        print(f"\n{'='*80}")
        print(f"Finding matching workers...")
        print(f"{'='*80}\n")

        # Find matching workers
        matches = matching_service.find_workers_for_gig(
            gig,
            min_score=0.2,  # Lower threshold for testing
            max_results=10
        )

        if not matches:
            print(f"❌ No matching workers found")
            return

        print(f"✅ Found {len(matches)} matching worker(s):\n")

        for idx, match in enumerate(matches, 1):
            worker = match['worker']
            breakdown = match['breakdown']

            print(f"👤 Match #{idx} - {match['match_percentage']}% Match")
            print(f"   Name: {worker.full_name or worker.username}")
            print(f"   Email: {worker.email}")
            print(f"   Rating: {'⭐' * int(worker.rating or 0)} ({worker.rating or 0:.1f}/5.0)")
            print(f"   Completed Gigs: {worker.completed_gigs or 0}")

            if breakdown['matched_skills']:
                print(f"   ✓ Matched Skills: {', '.join(breakdown['matched_skills'])}")

            print()


def show_menu():
    """Show interactive menu"""
    print(f"\n{'='*80}")
    print(f"GigHala AI Matching Test Menu")
    print(f"{'='*80}\n")
    print("1. Test matching for a specific worker")
    print("2. Test matching for all workers")
    print("3. Test finding workers for a specific gig")
    print("4. Exit")
    print()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'worker' and len(sys.argv) > 2:
            user_id = int(sys.argv[2])
            hours_back = int(sys.argv[3]) if len(sys.argv) > 3 else 24
            test_single_worker_matching(user_id, hours_back)

        elif command == 'all':
            hours_back = int(sys.argv[2]) if len(sys.argv) > 2 else 24
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5
            test_all_workers_matching(hours_back, limit)

        elif command == 'gig' and len(sys.argv) > 2:
            gig_id = int(sys.argv[2])
            test_gig_matching(gig_id)

        else:
            print("\nUsage:")
            print("  python test_matching.py worker <user_id> [hours_back]")
            print("  python test_matching.py all [hours_back] [limit]")
            print("  python test_matching.py gig <gig_id>")
            print("\nExamples:")
            print("  python test_matching.py worker 1 24")
            print("  python test_matching.py all 48 10")
            print("  python test_matching.py gig 5")

    else:
        # Interactive mode
        while True:
            show_menu()
            choice = input("Select an option (1-4): ").strip()

            if choice == '1':
                user_id = input("Enter worker user ID: ").strip()
                hours_back = input("Hours back to search (default 24): ").strip() or "24"
                try:
                    test_single_worker_matching(int(user_id), int(hours_back))
                except ValueError:
                    print("❌ Invalid input")

            elif choice == '2':
                hours_back = input("Hours back to search (default 24): ").strip() or "24"
                limit = input("Max workers to show (default 5): ").strip() or "5"
                try:
                    test_all_workers_matching(int(hours_back), int(limit))
                except ValueError:
                    print("❌ Invalid input")

            elif choice == '3':
                gig_id = input("Enter gig ID: ").strip()
                try:
                    test_gig_matching(int(gig_id))
                except ValueError:
                    print("❌ Invalid input")

            elif choice == '4':
                print("Goodbye!")
                break

            else:
                print("❌ Invalid option")

            input("\nPress Enter to continue...")
