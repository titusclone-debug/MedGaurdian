"""
Dedicated CLI Seeding Script for NABH Ontology.
Run out-of-band to seed the versioned reference ontology.

Example:
    python backend/scripts/seed_nabh_ontology.py --edition 6.0
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.nabh.seeder import seed_versioned_ontology
from app.nabh.seed_health import check_nabh_seed_health

def main():
    parser = argparse.ArgumentParser(description="Seed NABH Ontology Reference Data")
    parser.add_argument(
        "--edition",
        type=str,
        default="6.0",
        help="Target edition version to seed (default: 6.0)"
    )
    args = parser.parse_args()

    print("=" * 72)
    print(f"MedGuardian Dedicated Seeder: Edition {args.edition}")
    print("=" * 72)

    db = SessionLocal()
    try:
        # Check pre-seed health
        pre_health = check_nabh_seed_health(db, target_version=args.edition)
        print(f"Pre-seed Health check: {'HEALTHY' if pre_health['is_healthy'] else 'UNHEALTHY'}")
        print(f"  - Chapters: {pre_health['chapters_count']}/10")
        print(f"  - Requirements (Objective Elements): {pre_health['objective_elements_count']}")
        print(f"  - Citations: {pre_health['citations_count']}")
        print(f"  - Evidence Requirements: {pre_health['evidence_requirements_count']}")
        print(f"  - Missing Chapters: {pre_health['missing_chapters']}")
        print("-" * 72)

        # Trigger seeding transaction
        print("🌱 Seeding database transaction in progress...")
        seed_versioned_ontology(db, "app/nabh/data", target_version=args.edition)
        print("✅ Seeding transaction committed successfully.")
        print("-" * 72)

        # Check post-seed health
        post_health = check_nabh_seed_health(db, target_version=args.edition)
        print(f"Post-seed Health check: {'HEALTHY' if post_health['is_healthy'] else 'UNHEALTHY'}")
        print(f"  - Chapters: {post_health['chapters_count']}/10")
        print(f"  - Requirements (Objective Elements): {post_health['objective_elements_count']}")
        print(f"  - Citations: {post_health['citations_count']}")
        print(f"  - Evidence Requirements: {post_health['evidence_requirements_count']}")
        
        if not post_health["is_healthy"]:
            print("❌ ERROR: Post-seed health check failed. Ontology is incomplete.")
            sys.exit(1)

        print("🎉 Seeding verified successfully. DB is healthy and ready.")
        sys.exit(0)

    except Exception as e:
        print(f"❌ CRITICAL: Seeding failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
