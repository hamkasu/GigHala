"""
GigHala Worker-Gig Matching Service
AI-powered matching algorithm to connect workers with relevant gig opportunities
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from sqlalchemy import and_, or_
import logging

logger = logging.getLogger(__name__)


class GigMatchingService:
    """
    Intelligent matching service that scores and ranks gigs for workers
    based on skills, location, category, and other factors.
    """

    def __init__(self, db, User, Gig, WorkerSpecialization, calculate_distance):
        """
        Initialize the matching service with database models and helper functions.

        Args:
            db: SQLAlchemy database instance
            User: User model class
            Gig: Gig model class
            WorkerSpecialization: WorkerSpecialization model class
            calculate_distance: Function to calculate distance between coordinates
        """
        self.db = db
        self.User = User
        self.Gig = Gig
        self.WorkerSpecialization = WorkerSpecialization
        self.calculate_distance = calculate_distance

        # Matching weights for scoring algorithm
        self.WEIGHT_SKILLS = 0.40  # 40% - Most important factor
        self.WEIGHT_CATEGORY = 0.25  # 25% - Category specialization
        self.WEIGHT_LOCATION = 0.20  # 20% - Distance/proximity
        self.WEIGHT_BUDGET = 0.10  # 10% - Budget compatibility
        self.WEIGHT_FRESHNESS = 0.05  # 5% - Newer gigs scored slightly higher

        # Matching thresholds
        self.MIN_MATCH_SCORE = 0.3  # Only send gigs with >30% match
        self.MAX_DISTANCE_KM = 50  # Max distance for on-site gigs
        self.MAX_GIGS_PER_EMAIL = 10  # Limit gigs per notification

    def get_worker_skills(self, user) -> set:
        """
        Extract all skills for a worker from their profile and specializations.

        Args:
            user: User object (worker)

        Returns:
            Set of lowercase skill strings
        """
        skills = set()

        # Get skills from main profile
        if user.skills:
            try:
                profile_skills = json.loads(user.skills) if isinstance(user.skills, str) else user.skills
                if isinstance(profile_skills, list):
                    skills.update(skill.lower().strip() for skill in profile_skills if skill)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse skills for user {user.id}")

        # Get skills from specializations
        specializations = self.WorkerSpecialization.query.filter_by(user_id=user.id).all()
        for spec in specializations:
            if spec.skills:
                try:
                    spec_skills = json.loads(spec.skills) if isinstance(spec.skills, str) else spec.skills
                    if isinstance(spec_skills, list):
                        skills.update(skill.lower().strip() for skill in spec_skills if skill)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse specialization skills for user {user.id}")

        return skills

    def get_gig_required_skills(self, gig) -> set:
        """
        Extract required skills from a gig.

        Args:
            gig: Gig object

        Returns:
            Set of lowercase skill strings
        """
        skills = set()

        if gig.skills_required:
            try:
                required = json.loads(gig.skills_required) if isinstance(gig.skills_required, str) else gig.skills_required
                if isinstance(required, list):
                    skills.update(skill.lower().strip() for skill in required if skill)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse skills_required for gig {gig.id}")

        return skills

    def calculate_skill_match_score(self, worker_skills: set, gig_skills: set) -> float:
        """
        Calculate skill match score using Jaccard similarity and weighted matching.

        Args:
            worker_skills: Set of worker's skills
            gig_skills: Set of gig's required skills

        Returns:
            Score between 0.0 and 1.0
        """
        if not gig_skills:
            # If gig has no specific skill requirements, give moderate score
            return 0.5 if worker_skills else 0.3

        if not worker_skills:
            return 0.0

        # Calculate Jaccard similarity (intersection / union)
        intersection = worker_skills & gig_skills
        union = worker_skills | gig_skills

        jaccard_score = len(intersection) / len(union) if union else 0.0

        # Also calculate coverage (what % of required skills does worker have?)
        coverage_score = len(intersection) / len(gig_skills) if gig_skills else 0.0

        # Weighted average: 60% coverage (can they do the job?), 40% Jaccard (overall fit)
        final_score = (coverage_score * 0.6) + (jaccard_score * 0.4)

        return final_score

    def calculate_category_match_score(self, user, gig) -> float:
        """
        Calculate category match score based on worker specializations.

        Args:
            user: User object (worker)
            gig: Gig object

        Returns:
            Score between 0.0 and 1.0
        """
        if not gig.category:
            return 0.5  # Neutral score if no category

        # Check if worker has specialization in this category
        from app import Category
        category = Category.query.filter_by(slug=gig.category).first()

        if not category:
            return 0.5

        specialization = self.WorkerSpecialization.query.filter_by(
            user_id=user.id,
            category_id=category.id
        ).first()

        # Full match if specialized in this category
        if specialization:
            return 1.0

        # Partial match if they have any specializations (shows they're active)
        has_any_specialization = self.WorkerSpecialization.query.filter_by(user_id=user.id).first()
        if has_any_specialization:
            return 0.3

        return 0.0

    def calculate_location_match_score(self, user, gig) -> float:
        """
        Calculate location match score based on distance.

        Args:
            user: User object (worker)
            gig: Gig object

        Returns:
            Score between 0.0 and 1.0
        """
        # Remote gigs always score perfectly
        if gig.is_remote:
            return 1.0

        # If either party doesn't have coordinates, give moderate score
        if not all([user.latitude, user.longitude, gig.latitude, gig.longitude]):
            return 0.5

        try:
            distance = self.calculate_distance(
                user.latitude, user.longitude,
                gig.latitude, gig.longitude
            )

            # Score based on distance (closer is better)
            if distance <= 5:  # Within 5km
                return 1.0
            elif distance <= 15:  # Within 15km
                return 0.8
            elif distance <= 30:  # Within 30km
                return 0.6
            elif distance <= self.MAX_DISTANCE_KM:  # Within max distance
                return 0.4
            else:  # Too far
                return 0.1

        except Exception as e:
            logger.error(f"Error calculating distance: {e}")
            return 0.5

    def calculate_budget_match_score(self, user, gig) -> float:
        """
        Calculate budget match score based on worker's average earnings and gig budget.

        Args:
            user: User object (worker)
            gig: Gig object

        Returns:
            Score between 0.0 and 1.0
        """
        if not gig.budget_min and not gig.budget_max:
            return 0.7  # No budget specified, moderately attractive

        # Calculate worker's average gig value (if they have earnings)
        avg_earnings_per_gig = 0
        if user.completed_gigs > 0 and user.total_earnings:
            avg_earnings_per_gig = user.total_earnings / user.completed_gigs

        gig_budget = gig.budget_max or gig.budget_min or 0

        # For new workers or if no earnings data, any budget is acceptable
        if avg_earnings_per_gig == 0:
            return 0.8

        # Score based on budget relative to worker's usual rate
        ratio = gig_budget / avg_earnings_per_gig if avg_earnings_per_gig > 0 else 1.0

        if ratio >= 1.2:  # 20% above average - very attractive
            return 1.0
        elif ratio >= 0.8:  # Within 20% of average - good match
            return 0.9
        elif ratio >= 0.6:  # Somewhat below average
            return 0.7
        elif ratio >= 0.4:  # Significantly below average
            return 0.5
        else:  # Too low
            return 0.3

    def calculate_freshness_score(self, gig) -> float:
        """
        Calculate freshness score - newer gigs are slightly preferred.

        Args:
            gig: Gig object

        Returns:
            Score between 0.0 and 1.0
        """
        if not gig.created_at:
            return 0.5

        age_hours = (datetime.utcnow() - gig.created_at).total_seconds() / 3600

        if age_hours <= 6:  # Very fresh
            return 1.0
        elif age_hours <= 24:  # Today
            return 0.9
        elif age_hours <= 72:  # Last 3 days
            return 0.7
        else:
            return 0.5

    def calculate_match_score(self, user, gig) -> Tuple[float, Dict[str, float]]:
        """
        Calculate overall match score between a worker and a gig.

        Args:
            user: User object (worker)
            gig: Gig object

        Returns:
            Tuple of (overall_score, breakdown_dict)
        """
        worker_skills = self.get_worker_skills(user)
        gig_skills = self.get_gig_required_skills(gig)

        # Calculate individual scores
        skill_score = self.calculate_skill_match_score(worker_skills, gig_skills)
        category_score = self.calculate_category_match_score(user, gig)
        location_score = self.calculate_location_match_score(user, gig)
        budget_score = self.calculate_budget_match_score(user, gig)
        freshness_score = self.calculate_freshness_score(gig)

        # Calculate weighted overall score
        overall_score = (
            skill_score * self.WEIGHT_SKILLS +
            category_score * self.WEIGHT_CATEGORY +
            location_score * self.WEIGHT_LOCATION +
            budget_score * self.WEIGHT_BUDGET +
            freshness_score * self.WEIGHT_FRESHNESS
        )

        breakdown = {
            'skill_score': skill_score,
            'category_score': category_score,
            'location_score': location_score,
            'budget_score': budget_score,
            'freshness_score': freshness_score,
            'overall_score': overall_score,
            'matched_skills': list(worker_skills & gig_skills) if gig_skills else []
        }

        return overall_score, breakdown

    def find_matching_gigs_for_worker(
        self,
        user,
        hours_back: int = 24,
        min_score: Optional[float] = None,
        max_results: Optional[int] = None
    ) -> List[Dict]:
        """
        Find and rank matching gigs for a specific worker.

        Args:
            user: User object (worker)
            hours_back: Look for gigs created in the last N hours
            min_score: Minimum match score threshold (default: self.MIN_MATCH_SCORE)
            max_results: Maximum number of results (default: self.MAX_GIGS_PER_EMAIL)

        Returns:
            List of dicts with gig and match information, sorted by score
        """
        if min_score is None:
            min_score = self.MIN_MATCH_SCORE
        if max_results is None:
            max_results = self.MAX_GIGS_PER_EMAIL

        # Query open gigs from the last N hours
        time_threshold = datetime.utcnow() - timedelta(hours=hours_back)

        available_gigs = self.Gig.query.filter(
            and_(
                self.Gig.status == 'open',
                self.Gig.created_at >= time_threshold,
                self.Gig.client_id != user.id  # Don't match workers with their own gigs
            )
        ).all()

        matches = []

        for gig in available_gigs:
            score, breakdown = self.calculate_match_score(user, gig)

            if score >= min_score:
                matches.append({
                    'gig': gig,
                    'score': score,
                    'breakdown': breakdown,
                    'match_percentage': int(score * 100)
                })

        # Sort by score (highest first) and limit results
        matches.sort(key=lambda x: x['score'], reverse=True)

        return matches[:max_results]

    def find_workers_for_gig(
        self,
        gig,
        min_score: Optional[float] = None,
        max_results: int = 50
    ) -> List[Dict]:
        """
        Find and rank workers who match a specific gig.
        Useful for notifying qualified workers when a new gig is posted.

        Args:
            gig: Gig object
            min_score: Minimum match score threshold
            max_results: Maximum number of workers to return

        Returns:
            List of dicts with worker and match information, sorted by score
        """
        if min_score is None:
            min_score = self.MIN_MATCH_SCORE

        # Query active freelancers who want email notifications
        from app import NotificationPreference

        workers = self.db.session.query(self.User).join(
            NotificationPreference,
            self.User.id == NotificationPreference.user_id,
            isouter=True
        ).filter(
            and_(
                or_(
                    self.User.user_type == 'freelancer',
                    self.User.user_type == 'both'
                ),
                self.User.id != gig.client_id,  # Don't notify the client who posted it
                or_(
                    NotificationPreference.email_new_gig == True,
                    NotificationPreference.email_new_gig == None  # Default is True
                )
            )
        ).all()

        matches = []

        for worker in workers:
            score, breakdown = self.calculate_match_score(worker, gig)

            if score >= min_score:
                matches.append({
                    'worker': worker,
                    'score': score,
                    'breakdown': breakdown,
                    'match_percentage': int(score * 100)
                })

        # Sort by score (highest first) and limit results
        matches.sort(key=lambda x: x['score'], reverse=True)

        return matches[:max_results]

    def get_all_worker_matches(
        self,
        hours_back: int = 24,
        min_score: Optional[float] = None
    ) -> Dict[int, List[Dict]]:
        """
        Get matched gigs for all active workers.
        Used for batch email notifications.

        Args:
            hours_back: Look for gigs created in the last N hours
            min_score: Minimum match score threshold

        Returns:
            Dict mapping user_id to list of matched gigs
        """
        if min_score is None:
            min_score = self.MIN_MATCH_SCORE

        # Get all active freelancers who want email notifications
        from app import NotificationPreference

        workers = self.db.session.query(self.User).join(
            NotificationPreference,
            self.User.id == NotificationPreference.user_id,
            isouter=True
        ).filter(
            and_(
                or_(
                    self.User.user_type == 'freelancer',
                    self.User.user_type == 'both'
                ),
                or_(
                    NotificationPreference.email_new_gig == True,
                    NotificationPreference.email_new_gig == None
                )
            )
        ).all()

        worker_matches = {}

        for worker in workers:
            matches = self.find_matching_gigs_for_worker(
                worker,
                hours_back=hours_back,
                min_score=min_score
            )

            if matches:  # Only include workers who have matches
                worker_matches[worker.id] = matches

        return worker_matches
